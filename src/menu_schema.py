"""Structured schema and validation for AI-extracted matcha menu items."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DrinkCategory = Literal[
    "Matcha",
    "Matcha Latte",
    "Matcha Soda",
    "Matcha Smoothie",
    "Matcha Dessert",
]


class ExtractedMenuItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drink_name: str = Field(min_length=1)
    drink_category: DrinkCategory
    flavor: str | None = None
    available_hot: bool | None = None
    available_iced: bool | None = None
    sizes: list[str] = Field(default_factory=list)
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    price_is_starting: bool = False
    milk_options: list[str] = Field(default_factory=list)
    matcha_type_claim: list[str] = Field(default_factory=list)
    evidence: str = Field(
        min_length=1,
        description="Short verbatim menu fragment supporting the extracted item.",
    )

    @field_validator("flavor")
    @classmethod
    def normalize_flavor(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        preparation_styles = {
            "cream top",
            "cold foam",
            "matcha cream",
            "matcha foam",
            "salted cream",
            "salted cheese",
        }
        if cleaned.lower() in preparation_styles:
            return "Original"
        if "/" in cleaned:
            cleaned = "; ".join(
                part.strip() for part in cleaned.split("/") if part.strip()
            )
        return cleaned or None

    @field_validator("milk_options")
    @classmethod
    def normalize_milk_options(cls, values: list[str]) -> list[str]:
        canonical = {
            "whole": "Whole",
            "whole milk": "Whole",
            "2%": "2%",
            "2% milk": "2%",
            "organic 2%": "2%",
            "organic 2% milk": "2%",
            "oat": "Oat",
            "oat milk": "Oat",
            "almond": "Almond",
            "almond milk": "Almond",
            "house-made almond": "Almond",
            "house-made almond milk": "Almond",
            "coconut": "Coconut",
            "coconut milk": "Coconut",
            "soy": "Soy",
            "soy milk": "Soy",
            "corn": "Corn",
            "corn milk": "Corn",
            "horchata": "Horchata",
        }
        normalized = []
        for value in values:
            key = value.strip().lower()
            # Generic "milk" in an ingredient list is not an explicit milk choice.
            if key == "milk":
                continue
            normalized.append(canonical.get(key, value.strip()))
        return list(dict.fromkeys(value for value in normalized if value))

    @field_validator("matcha_type_claim")
    @classmethod
    def normalize_matcha_claims(cls, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            cleaned = value.strip()
            key = cleaned.lower().replace("-", " ")
            if "ceremonial" in key:
                cleaned = "Ceremonial"
            elif key in {"uji", "uji matcha"}:
                cleaned = "Uji"
            elif " - " in cleaned:
                # Keep the named matcha/cultivar; location detail remains in evidence.
                cleaned = cleaned.split(" - ", 1)[0].strip()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    @model_validator(mode="after")
    def apply_defaults_and_validate_price_range(self) -> "ExtractedMenuItem":
        if (
            self.drink_category != "Matcha Dessert"
            and self.available_hot is not True
            and self.available_iced is None
        ):
            self.available_iced = True
        if self.min_price is None and self.max_price is not None:
            raise ValueError("max_price cannot exist without min_price")
        if self.price_is_starting:
            self.max_price = None
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must be less than or equal to max_price")
        return self


class MenuExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ExtractedMenuItem]
    extraction_notes: list[str] = Field(default_factory=list)


def openai_strict_json_schema() -> dict:
    """Return a JSON Schema compatible with OpenAI strict Structured Outputs."""
    schema = MenuExtraction.model_json_schema()

    def normalize(node: object) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["additionalProperties"] = False
                node["required"] = list(properties)
            for value in node.values():
                normalize(value)
        elif isinstance(node, list):
            for value in node:
                normalize(value)

    normalize(schema)
    return schema
