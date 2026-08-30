import unittest

from pydantic import ValidationError

from src.menu_schema import (
    ExtractedMenuItem,
    MenuExtraction,
    openai_strict_json_schema,
)


class MenuSchemaTests(unittest.TestCase):
    def test_unknown_max_price_stays_null(self):
        item = ExtractedMenuItem(
            drink_name="Matcha Latte",
            drink_category="Matcha Latte",
            flavor="Original",
            min_price=7.0,
            evidence="Matcha Latte $7",
        )
        self.assertIsNone(item.max_price)
        self.assertTrue(item.available_iced)

    def test_starting_price_clears_max_price(self):
        item = ExtractedMenuItem(
            drink_name="Matcha Latte",
            drink_category="Matcha Latte",
            min_price=7.0,
            max_price=7.0,
            price_is_starting=True,
            evidence="Matcha Latte $7.00+",
        )
        self.assertIsNone(item.max_price)

    def test_preparation_style_is_not_a_flavor(self):
        item = ExtractedMenuItem(
            drink_name="Salted Cream Top Matcha Latte",
            drink_category="Matcha Latte",
            flavor="Salted Cream",
            evidence="salted cream cold foam",
        )
        self.assertEqual(item.flavor, "Original")

    def test_normalizes_multiple_flavors(self):
        item = ExtractedMenuItem(
            drink_name="Matcha Taro/Ube Latte",
            drink_category="Matcha Latte",
            flavor="Taro/Ube",
            evidence="taro ube foam",
        )
        self.assertEqual(item.flavor, "Taro; Ube")

    def test_iced_default_does_not_apply_to_dessert(self):
        item = ExtractedMenuItem(
            drink_name="Matcha Soft Serve",
            drink_category="Matcha Dessert",
            evidence="Matcha Soft Serve",
        )
        self.assertIsNone(item.available_iced)

    def test_explicit_hot_does_not_imply_iced(self):
        item = ExtractedMenuItem(
            drink_name="Hot Matcha",
            drink_category="Matcha",
            available_hot=True,
            evidence="Hot Matcha",
        )
        self.assertIsNone(item.available_iced)

    def test_rejects_reversed_price_range(self):
        with self.assertRaises(ValidationError):
            ExtractedMenuItem(
                drink_name="Matcha Latte",
                drink_category="Matcha Latte",
                min_price=8.0,
                max_price=7.0,
                evidence="12 oz $8; 16 oz $7",
            )

    def test_rejects_unknown_category(self):
        with self.assertRaises(ValidationError):
            ExtractedMenuItem(
                drink_name="Matcha Cloud",
                drink_category="Cloud Drink",
                evidence="Matcha Cloud",
            )

    def test_menu_extraction_accepts_empty_notes(self):
        extraction = MenuExtraction(items=[], extraction_notes=[])
        self.assertEqual(extraction.items, [])

    def test_openai_schema_requires_every_property(self):
        schema = openai_strict_json_schema()
        self.assertEqual(set(schema["required"]), set(schema["properties"]))
        item_schema = schema["$defs"]["ExtractedMenuItem"]
        self.assertEqual(
            set(item_schema["required"]), set(item_schema["properties"])
        )

    def test_normalizes_claims_and_milk_options(self):
        item = ExtractedMenuItem(
            drink_name="Matcha Latte",
            drink_category="Matcha Latte",
            milk_options=[
                "milk", "oat milk", "Oat", "organic 2%", "house-made almond",
                "corn milk",
            ],
            matcha_type_claim=[
                "First-harvest ceremonial grade",
                "Ceremonial-grade",
                "Uji Matcha",
                "Kanayamidori - Kagoshima, Japan",
            ],
            evidence="Ceremonial-grade Uji matcha with oat milk",
        )
        self.assertEqual(item.milk_options, ["Oat", "2%", "Almond", "Corn"])
        self.assertEqual(
            item.matcha_type_claim, ["Ceremonial", "Uji", "Kanayamidori"]
        )


if __name__ == "__main__":
    unittest.main()
