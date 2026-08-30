"""Load analysis-ready Matcha Project datasets into SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data/processed"
DATABASE = PROCESSED / "seattle_matcha.db"


def build_flavor_bridge(menu: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for item in menu[["item_id", "shop_id", "flavor"]].itertuples(index=False):
        if pd.isna(item.flavor):
            continue
        for flavor in str(item.flavor).split(";"):
            flavor = flavor.strip()
            if flavor:
                rows.append(
                    {"item_id": item.item_id, "shop_id": item.shop_id, "flavor": flavor}
                )
    return pd.DataFrame(rows, columns=["item_id", "shop_id", "flavor"])


def main() -> None:
    shops = pd.read_csv(PROCESSED / "shops_analytics.csv")
    menu = pd.read_csv(PROCESSED / "menu_items_analytics.csv")
    flavors = build_flavor_bridge(menu)

    with sqlite3.connect(DATABASE) as connection:
        shops.to_sql("shops", connection, if_exists="replace", index=False)
        menu.to_sql("menu_items", connection, if_exists="replace", index=False)
        flavors.to_sql("menu_item_flavors", connection, if_exists="replace", index=False)
        connection.executescript(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_shops_shop_id
                ON shops(shop_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_menu_item_id
                ON menu_items(item_id);
            CREATE INDEX IF NOT EXISTS idx_menu_shop_id
                ON menu_items(shop_id);
            CREATE INDEX IF NOT EXISTS idx_menu_category
                ON menu_items(drink_category);
            CREATE INDEX IF NOT EXISTS idx_flavor_name
                ON menu_item_flavors(flavor);

            DROP VIEW IF EXISTS v_menu_enriched;
            CREATE VIEW v_menu_enriched AS
            SELECT
                m.*,
                s.shop_name,
                s.neighborhood,
                s.shop_type,
                s.google_rating,
                s.google_review_count,
                s.matcha_price_level
            FROM menu_items AS m
            INNER JOIN shops AS s USING (shop_id);
            """
        )

    print(f"Created {DATABASE.relative_to(ROOT)}")
    print(f"Loaded {len(shops)} shops, {len(menu)} menu items, {len(flavors)} flavor rows")


if __name__ == "__main__":
    main()
