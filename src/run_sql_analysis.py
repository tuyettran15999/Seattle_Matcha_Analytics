"""Run named SQLite business queries and export their results."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data/processed/seattle_matcha.db"
OUTPUT_DIR = ROOT / "reports/sql_results"

QUERIES = {
    "01_kpi_overview": """
        SELECT COUNT(*) total_shops, SUM(has_complete_menu) shops_with_complete_menu,
               SUM(avg_matcha_price IS NOT NULL) shops_with_price_data,
               ROUND(AVG(avg_matcha_price), 2) avg_shop_matcha_price,
               SUM(menu_item_count) total_menu_items
        FROM shops
    """,
    "02_top_menu_variety": """
        SELECT shop_id, shop_name, neighborhood, shop_type, menu_item_count,
               unique_flavor_count, ROUND(avg_matcha_price, 2) avg_matcha_price,
               google_rating
        FROM shops WHERE has_complete_menu = 1
        ORDER BY menu_item_count DESC, unique_flavor_count DESC, shop_name LIMIT 10
    """,
    "03_top_flavors": """
        SELECT flavor, COUNT(DISTINCT item_id) menu_item_count,
               COUNT(DISTINCT shop_id) shop_count
        FROM menu_item_flavors WHERE LOWER(flavor) <> 'original'
        GROUP BY flavor ORDER BY shop_count DESC, menu_item_count DESC, flavor LIMIT 15
    """,
    "04_category_summary": """
        SELECT drink_category, COUNT(*) menu_item_count,
               COUNT(DISTINCT shop_id) shop_count,
               ROUND(AVG(analytics_price), 2) avg_price
        FROM menu_items GROUP BY drink_category ORDER BY menu_item_count DESC
    """,
    "05_shop_type_summary": """
        SELECT shop_type, COUNT(*) shop_count, SUM(has_complete_menu) complete_menu_count,
               ROUND(AVG(avg_matcha_price), 2) avg_matcha_price,
               ROUND(AVG(menu_item_count), 1) avg_menu_items,
               ROUND(AVG(unique_flavor_count), 1) avg_unique_flavors
        FROM shops GROUP BY shop_type ORDER BY avg_menu_items DESC
    """,
    "06_neighborhood_summary": """
        SELECT neighborhood, COUNT(*) shop_count,
               ROUND(AVG(google_rating), 2) avg_google_rating,
               SUM(menu_item_count) verified_menu_items
        FROM shops GROUP BY neighborhood
        ORDER BY shop_count DESC, verified_menu_items DESC, neighborhood
    """,
    "07_matcha_score": """
        WITH eligible AS (
            SELECT * FROM shops WHERE has_complete_menu = 1
              AND avg_matcha_price IS NOT NULL AND google_rating IS NOT NULL
              AND google_review_count IS NOT NULL
        ), normalized AS (
            SELECT *,
              (google_rating-MIN(google_rating) OVER())/NULLIF(MAX(google_rating) OVER()-MIN(google_rating) OVER(),0) rating_score,
              (LOG(google_review_count+1)-MIN(LOG(google_review_count+1)) OVER())/NULLIF(MAX(LOG(google_review_count+1)) OVER()-MIN(LOG(google_review_count+1)) OVER(),0) popularity_score,
              (menu_item_count-MIN(menu_item_count) OVER())*1.0/NULLIF(MAX(menu_item_count) OVER()-MIN(menu_item_count) OVER(),0) variety_score,
              1-((avg_matcha_price-MIN(avg_matcha_price) OVER())/NULLIF(MAX(avg_matcha_price) OVER()-MIN(avg_matcha_price) OVER(),0)) affordability_score
            FROM eligible
        )
        SELECT shop_id, shop_name, neighborhood, ROUND(google_rating,1) google_rating,
               google_review_count, menu_item_count, ROUND(avg_matcha_price,2) avg_matcha_price,
               ROUND(100*(0.35*rating_score+0.20*popularity_score+0.30*variety_score+0.15*affordability_score),1) matcha_score
        FROM normalized ORDER BY matcha_score DESC, shop_name LIMIT 10
    """,
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE) as connection:
        for name, query in QUERIES.items():
            result = pd.read_sql_query(query, connection)
            result.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)
            print(f"{name}: {len(result)} rows")


if __name__ == "__main__":
    main()
