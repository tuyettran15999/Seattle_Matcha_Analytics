"""Extract structured matcha menu records with the OpenAI Responses API."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from menu_prompt import SYSTEM_PROMPT, build_user_prompt
from menu_schema import MenuExtraction, openai_strict_json_schema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "ai_menu_extractions"
PROCESSED_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "ai_menu_extractions"
OVERRIDES_PATH = PROJECT_ROOT / "data" / "raw" / "menu_item_overrides.csv"


def apply_manual_overrides(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Apply auditable human-review corrections without changing raw AI JSON."""
    if dataframe.empty or not OVERRIDES_PATH.exists():
        return dataframe

    overrides = pd.read_csv(OVERRIDES_PATH, keep_default_na=False)
    required = {"shop_id", "drink_name", "field", "value", "reason"}
    if not required.issubset(overrides.columns):
        raise ValueError(f"Override file must contain columns: {sorted(required)}")

    for override in overrides.itertuples(index=False):
        if override.field not in dataframe.columns:
            raise ValueError(f"Unknown override field: {override.field}")
        mask = (
            dataframe["shop_id"].eq(override.shop_id)
            & dataframe["drink_name"].eq(override.drink_name)
        )
        if not mask.any():
            continue

        value: object = override.value
        if override.value == "__NULL__":
            value = pd.NA
        elif override.field == "price_is_starting":
            value = override.value.strip().lower() == "true"
        elif override.field in {"min_price", "max_price"}:
            value = float(override.value)
        dataframe.loc[mask, override.field] = value

    return dataframe


def flatten_extraction(
    extraction: MenuExtraction,
    shop_id: str,
    menu_url: str,
    menu_source: str,
) -> pd.DataFrame:
    rows = []
    for sequence, item in enumerate(extraction.items, start=1):
        rows.append(
            {
                "item_id": f"{shop_id}-AI-{sequence:03d}",
                "shop_id": shop_id,
                "drink_name": item.drink_name,
                "drink_category": item.drink_category,
                "flavor": item.flavor,
                "available_hot": item.available_hot,
                "available_iced": item.available_iced,
                "size": "; ".join(item.sizes) or None,
                "min_price": item.min_price,
                "max_price": item.max_price,
                "price_is_starting": item.price_is_starting,
                "milk_options": "; ".join(item.milk_options) or None,
                "matcha_type_claim": "; ".join(item.matcha_type_claim) or None,
                "menu_source": menu_source,
                "menu_url": menu_url,
                "date_collected": date.today().isoformat(),
                "extraction_evidence": item.evidence,
                "review_status": "Needs human review",
            }
        )
    return apply_manual_overrides(pd.DataFrame(rows))


def validate_shop_id(shop_id: str) -> None:
    shops_path = PROJECT_ROOT / "data" / "processed" / "shops_seattle_clean.csv"
    shops = pd.read_csv(shops_path, usecols=["shop_id"])
    if shop_id not in set(shops["shop_id"]):
        raise ValueError(f"Unknown shop_id: {shop_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shop-id", required=True)
    parser.add_argument("--menu-url", required=True)
    parser.add_argument("--menu-text-file", type=Path, required=True)
    parser.add_argument("--menu-source", default="Official Website")
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print the request summary without calling the API.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_shop_id(args.shop_id)
    menu_text = args.menu_text_file.read_text(encoding="utf-8").strip()
    if not menu_text:
        raise ValueError("Menu text file is empty")

    if args.dry_run:
        print(f"Dry run OK: {args.shop_id}, {len(menu_text)} menu characters")
        print(f"Model: {args.model}")
        print("No API request was sent.")
        return

    load_dotenv(PROJECT_ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Missing OPENAI_API_KEY in .env")

    client = OpenAI()
    response = client.responses.create(
        model=args.model,
        reasoning={"effort": "low"},
        store=False,
        input=[
            {"role": "developer", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(args.shop_id, args.menu_url, menu_text),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "matcha_menu_extraction",
                "schema": openai_strict_json_schema(),
                "strict": True,
            }
        },
    )

    payload = json.loads(response.output_text)
    extraction = MenuExtraction.model_validate(payload)

    RAW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_OUTPUT_DIR / f"{args.shop_id.lower()}_extraction.json"
    csv_path = PROCESSED_OUTPUT_DIR / f"{args.shop_id.lower()}_menu_items.csv"

    raw_path.write_text(
        json.dumps(
            {
                "response_id": response.id,
                "model": response.model,
                "shop_id": args.shop_id,
                "menu_url": args.menu_url,
                "extraction": extraction.model_dump(),
                "usage": response.usage.model_dump() if response.usage else None,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    dataframe = flatten_extraction(
        extraction, args.shop_id, args.menu_url, args.menu_source
    )
    dataframe.to_csv(csv_path, index=False)

    print(f"Extracted {len(dataframe)} matcha items")
    print(f"Raw JSON: {raw_path.relative_to(PROJECT_ROOT)}")
    print(f"Review CSV: {csv_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
