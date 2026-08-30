"""Create analysis-ready menu and shop datasets from reviewed Seattle data."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data/processed"
MENU_INPUT = PROCESSED / "menu_items_seattle_reviewed.csv"
SHOPS_INPUT = PROCESSED / "shops_seattle_clean.csv"
TRACKER_INPUT = PROCESSED / "menu_collection_tracker.csv"
MENU_OUTPUT = PROCESSED / "menu_items_analytics.csv"
SHOPS_OUTPUT = PROCESSED / "shops_analytics.csv"
QUALITY_OUTPUT = PROCESSED / "data_quality_report.csv"
METADATA_OUTPUT = PROCESSED / "analytics_metadata.json"


def count_options(series: pd.Series) -> pd.Series:
    """Count semicolon-separated options while preserving missing as zero."""
    return series.fillna("").map(
        lambda value: len([part for part in str(value).split(";") if part.strip()])
    )


def assign_price_levels(
    average_prices: pd.Series,
) -> tuple[pd.Series, float, float]:
    """Assign Low/Medium/High using tertiles of observed shop average prices."""
    observed = average_prices.dropna()
    lower = float(observed.quantile(1 / 3))
    upper = float(observed.quantile(2 / 3))

    def classify(value: float) -> str | pd.NA:
        if pd.isna(value):
            return pd.NA
        if value <= lower:
            return "Low"
        if value <= upper:
            return "Medium"
        return "High"

    return average_prices.map(classify), lower, upper


def prepare_menu(menu: pd.DataFrame) -> pd.DataFrame:
    data = menu.copy()
    for column in ["available_hot", "available_iced"]:
        data[column] = data[column].map(
            {True: True, False: False, "True": True, "False": False}
        ).astype("boolean")

    # A price range may reflect size or another published variant. The midpoint
    # is used as a comparable representative price; a lone min_price remains the
    # best available observed/starting price.
    data["analytics_price"] = data[["min_price", "max_price"]].mean(
        axis=1, skipna=True
    )
    data["has_price"] = data["analytics_price"].notna()
    data["has_flavor"] = data["flavor"].notna()
    data["is_flavored"] = (
        data["flavor"].notna()
        & data["flavor"].str.casefold().ne("original")
    )
    data["has_matcha_type_claim"] = data["matcha_type_claim"].notna()
    data["milk_option_count"] = count_options(data["milk_options"])
    data["size_option_count"] = count_options(data["size"])
    return data


def build_shops(
    shops: pd.DataFrame, menu: pd.DataFrame, tracker: pd.DataFrame
) -> tuple[pd.DataFrame, float, float]:
    flavored = menu.loc[menu["is_flavored"]].groupby("shop_id").size()
    hot = menu.loc[menu["available_hot"].eq(True)].groupby("shop_id").size()
    iced = menu.loc[menu["available_iced"].eq(True)].groupby("shop_id").size()

    metrics = menu.groupby("shop_id").agg(
        menu_item_count=("item_id", "nunique"),
        priced_item_count=("has_price", "sum"),
        avg_matcha_price=("analytics_price", "mean"),
        median_matcha_price=("analytics_price", "median"),
        min_matcha_price=("analytics_price", "min"),
        max_matcha_price=("analytics_price", "max"),
        unique_flavor_count=("flavor", "nunique"),
        unique_category_count=("drink_category", "nunique"),
        matcha_claim_item_count=("has_matcha_type_claim", "sum"),
    )
    metrics["flavored_item_count"] = flavored
    metrics["hot_item_count"] = hot
    metrics["iced_item_count"] = iced
    count_columns = [column for column in metrics if column.endswith("_count")]
    metrics[count_columns] = metrics[count_columns].fillna(0).astype(int)
    metrics["price_coverage_pct"] = (
        metrics["priced_item_count"] / metrics["menu_item_count"] * 100
    ).round(1)
    metrics["flavored_item_ratio"] = (
        metrics["flavored_item_count"] / metrics["menu_item_count"]
    ).round(3)
    price_level, lower, upper = assign_price_levels(metrics["avg_matcha_price"])
    metrics["matcha_price_level"] = price_level

    result = shops.merge(metrics.reset_index(), on="shop_id", how="left")
    status = tracker[["shop_id", "raw_text_status", "human_review_status"]]
    result = result.merge(status, on="shop_id", how="left")
    result["has_complete_menu"] = result["raw_text_status"].eq(
        "Full menu captured"
    )

    eligible = (
        result["has_complete_menu"]
        & result["avg_matcha_price"].notna()
        & result["google_rating"].notna()
        & result["google_review_count"].notna()
    )

    def minmax(values: pd.Series) -> pd.Series:
        minimum = values.min()
        spread = values.max() - minimum
        if spread == 0:
            return pd.Series(1.0, index=values.index)
        return (values - minimum) / spread

    scored = result.loc[eligible].copy()
    rating_score = minmax(scored["google_rating"])
    popularity_score = minmax(scored["google_review_count"].map(math.log1p))
    variety_score = minmax(scored["menu_item_count"])
    affordability_score = 1 - minmax(scored["avg_matcha_price"])
    result["matcha_score"] = pd.NA
    result.loc[eligible, "matcha_score"] = (
        100
        * (
            0.35 * rating_score
            + 0.20 * popularity_score
            + 0.30 * variety_score
            + 0.15 * affordability_score
        )
    ).round(1)
    result["matcha_score"] = pd.to_numeric(result["matcha_score"])
    result["matcha_score_rank"] = (
        result["matcha_score"].rank(method="min", ascending=False).astype("Int64")
    )

    for column in count_columns:
        result[column] = result[column].fillna(0).astype(int)
    return result, lower, upper


def quality_report(menu: pd.DataFrame, shops: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dataset_name, data in [("menu_items", menu), ("shops", shops)]:
        for column in data.columns:
            rows.append(
                {
                    "dataset": dataset_name,
                    "column": column,
                    "row_count": len(data),
                    "missing_count": int(data[column].isna().sum()),
                    "missing_pct": round(float(data[column].isna().mean() * 100), 1),
                    "unique_count": int(data[column].nunique(dropna=True)),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    menu = prepare_menu(pd.read_csv(MENU_INPUT))
    shops, lower, upper = build_shops(
        pd.read_csv(SHOPS_INPUT), menu, pd.read_csv(TRACKER_INPUT)
    )
    quality = quality_report(menu, shops)

    menu.to_csv(MENU_OUTPUT, index=False)
    shops.to_csv(SHOPS_OUTPUT, index=False)
    quality.to_csv(QUALITY_OUTPUT, index=False)
    METADATA_OUTPUT.write_text(
        json.dumps(
            {
                "analytics_price_definition": (
                    "Midpoint of min_price and max_price when both exist; "
                    "otherwise the available min_price."
                ),
                "matcha_price_level_method": "Tertiles of observed shop average prices",
                "low_max": round(lower, 2),
                "medium_max": round(upper, 2),
                "shops_with_complete_menu": int(shops["has_complete_menu"].sum()),
                "shops_with_price_metrics": int(shops["avg_matcha_price"].notna().sum()),
                "matcha_score_definition": {
                    "rating": 0.35,
                    "menu_variety": 0.30,
                    "log_review_popularity": 0.20,
                    "affordability": 0.15
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {len(menu)} analytics-ready menu items")
    print(f"Wrote {len(shops)} shops; {shops['has_complete_menu'].sum()} complete menus")
    print(f"Price levels: Low <= ${lower:.2f}; Medium <= ${upper:.2f}; High above")


if __name__ == "__main__":
    main()
