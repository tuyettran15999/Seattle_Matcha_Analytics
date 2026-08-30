"""Create stable, Tableau-ready CSV sources from the analytics datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from build_sqlite_database import build_flavor_bridge


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data/processed"
OUTPUT = ROOT / "data/tableau"


def main() -> None:
    shops = pd.read_csv(PROCESSED / "shops_analytics.csv")
    menu = pd.read_csv(PROCESSED / "menu_items_analytics.csv")
    flavors = build_flavor_bridge(menu)

    # Keep stable field order so Tableau sources do not shift between rebuilds.
    shops.to_csv(OUTPUT / "shops_dashboard.csv", index=False)
    menu.to_csv(OUTPUT / "menu_items_dashboard.csv", index=False)
    flavors.to_csv(OUTPUT / "menu_item_flavors_dashboard.csv", index=False)

    if shops["shop_id"].duplicated().any():
        raise ValueError("shops_dashboard must contain one row per shop_id")
    if menu["item_id"].duplicated().any():
        raise ValueError("menu_items_dashboard must contain one row per item_id")
    if not set(menu["shop_id"]).issubset(set(shops["shop_id"])):
        raise ValueError("Every menu shop_id must exist in shops_dashboard")
    if not set(flavors["item_id"]).issubset(set(menu["item_id"])):
        raise ValueError("Every flavor item_id must exist in menu_items_dashboard")

    print(f"Tableau sources: {len(shops)} shops, {len(menu)} items, {len(flavors)} flavor rows")


if __name__ == "__main__":
    main()
