"""Merge Google Places discovery files and deduplicate physical locations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "google_places"
OUTPUT_PATH = PROJECT_ROOT / "data" / "interim" / "shop_candidates_merged.csv"
EXCLUSIONS_PATH = PROJECT_ROOT / "data" / "raw" / "candidate_exclusions.csv"
QUALIFICATIONS_PATH = PROJECT_ROOT / "data" / "raw" / "candidate_qualifications.csv"


def join_unique(values: pd.Series) -> str:
    cleaned = {str(value).strip() for value in values.dropna() if str(value).strip()}
    return " | ".join(sorted(cleaned))


def main() -> None:
    paths = sorted(INPUT_DIR.glob("*.csv"))
    if not paths:
        raise SystemExit(f"No candidate CSV files found in {INPUT_DIR}")

    frames = [pd.read_csv(path) for path in paths]
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[combined["place_id"].notna()].copy()

    query_counts = combined.groupby("place_id")["discovery_query"].nunique()
    discovery_queries = combined.groupby("place_id")["discovery_query"].agg(join_unique)

    master = (
        combined.sort_values("date_collected_utc")
        .drop_duplicates(subset="place_id", keep="last")
        .set_index("place_id")
    )
    master["query_match_count"] = query_counts
    master["discovery_queries"] = discovery_queries
    master["city_scope_check"] = master["formatted_address"].str.contains(
        r"Seattle, WA", case=False, na=False
    )
    master = master.drop(columns=["discovery_query"]).reset_index()

    master["rejection_reason"] = pd.NA
    master["qualification_basis"] = pd.NA
    if QUALIFICATIONS_PATH.exists():
        qualifications = pd.read_csv(QUALIFICATIONS_PATH).set_index("place_id")
        qualified = master["place_id"].isin(qualifications.index)
        master.loc[qualified, "verification_status"] = "Qualified"
        master.loc[qualified, "qualification_basis"] = master.loc[
            qualified, "place_id"
        ].map(qualifications["qualification_basis"])

    if EXCLUSIONS_PATH.exists():
        exclusions = pd.read_csv(EXCLUSIONS_PATH).set_index("place_id")
        rejected = master["place_id"].isin(exclusions.index)
        master.loc[rejected, "verification_status"] = "Rejected"
        master.loc[rejected, "rejection_reason"] = master.loc[
            rejected, "place_id"
        ].map(exclusions["rejection_reason"])

    preferred_columns = [
        "place_id",
        "shop_name",
        "formatted_address",
        "city_scope_check",
        "primary_type",
        "google_types",
        "google_rating",
        "google_review_count",
        "website_url",
        "google_maps_url",
        "query_match_count",
        "discovery_queries",
        "verification_status",
        "qualification_basis",
        "rejection_reason",
        "date_collected_utc",
    ]
    master = master[preferred_columns].sort_values(
        ["query_match_count", "google_review_count"], ascending=[False, False]
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    master.to_csv(OUTPUT_PATH, index=False)

    print(f"Input rows: {len(combined)}")
    print(f"Unique physical locations: {len(master)}")
    print(f"Duplicate rows removed: {len(combined) - len(master)}")
    print(f"Outside Seattle address check: {(~master['city_scope_check']).sum()}")
    print(f"Manually rejected: {(master['verification_status'] == 'Rejected').sum()}")
    print(f"Menu-qualified: {(master['verification_status'] == 'Qualified').sum()}")
    print(f"Saved: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
