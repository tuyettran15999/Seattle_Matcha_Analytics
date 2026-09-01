"""Build the Seattle shops master from pilot shops and verified candidates."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_PATH = PROJECT_ROOT / "data" / "archive" / "pilot" / "shops_pilot.xlsx"
CANDIDATE_PATH = PROJECT_ROOT / "data" / "interim" / "shop_candidates_merged.csv"
PILOT_PLACE_ID_PATH = PROJECT_ROOT / "data" / "raw" / "pilot_place_id_lookup.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "interim" / "shops_clean.csv"

NEIGHBORHOOD_BY_SHOP_ID = {
    "SEA006": "Capitol Hill",
    "SEA007": "Downtown",
    "SEA008": "University District",
    "SEA009": "University District",
    "SEA010": "Denny Triangle",
    "SEA011": "Uptown",
    "SEA012": "Madrona",
    "SEA013": "Capitol Hill",
    "SEA014": "Pioneer Square",
    "SEA015": "Capitol Hill",
    "SEA016": "Denny Triangle",
    "SEA017": "University District",
    "SEA018": "Downtown",
    "SEA019": "Ballard",
    "SEA020": "Chinatown-International District",
    "SEA021": "University District",
    "SEA022": "Capitol Hill",
    "SEA023": "Capitol Hill",
    "SEA024": "Columbia City",
    "SEA025": "Downtown Waterfront",
    "SEA026": "First Hill",
    "SEA027": "Downtown",
    "SEA028": "Downtown",
}

SHOP_TYPE_BY_SHOP_ID = {
    "SEA006": "Matcha / Tea Shop",
    "SEA007": "Matcha / Tea Shop",
    "SEA008": "Matcha / Tea Shop",
    "SEA009": "Matcha / Tea Shop",
    "SEA010": "Matcha / Tea Shop",
    "SEA011": "Cafe / Coffee Shop",
    "SEA012": "Boba / Bubble Tea Shop",
    "SEA013": "Matcha / Tea Shop",
    "SEA014": "Bakery / Dessert Cafe",
    "SEA015": "Bakery / Dessert Cafe",
    "SEA016": "Matcha / Tea Shop",
    "SEA017": "Bakery / Dessert Cafe",
    "SEA018": "Matcha / Tea Shop",
    "SEA019": "Matcha / Tea Shop",
    "SEA020": "Cafe / Coffee Shop",
    "SEA021": "Boba / Bubble Tea Shop",
    "SEA022": "Boba / Bubble Tea Shop",
    "SEA023": "Bakery / Dessert Cafe",
    "SEA024": "Boba / Bubble Tea Shop",
    "SEA025": "Cafe / Coffee Shop",
    "SEA026": "Bakery / Dessert Cafe",
    "SEA027": "Cafe / Coffee Shop",
    "SEA028": "Cafe / Coffee Shop",
}

ADDRESS_BY_SHOP_ID = {
    "SEA028": "1000 4th Ave Fl 3, Seattle, WA 98104",
}


def normalize(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def main() -> None:
    pilot = pd.read_excel(PILOT_PATH)
    candidates = pd.read_csv(CANDIDATE_PATH)
    qualified = candidates.loc[candidates["verification_status"].eq("Qualified")].copy()
    pilot_place_ids = {}
    if PILOT_PLACE_ID_PATH.exists():
        lookup = pd.read_csv(PILOT_PLACE_ID_PATH)
        pilot_place_ids = lookup.set_index("shop_id")["google_place_id"].to_dict()

    pilot["_name_key"] = pilot["shop_name"].map(normalize)
    pilot["_address_key"] = pilot["address"].map(normalize)
    qualified["_name_key"] = qualified["shop_name"].map(normalize)
    qualified["_address_key"] = qualified["formatted_address"].map(normalize)

    # Address is the primary match because one brand may have several locations.
    pilot_by_address = {
        row["_address_key"]: index
        for index, row in pilot.iterrows()
        if row["_address_key"]
    }

    rows: list[dict] = []
    matched_pilot_indexes: set[int] = set()
    next_id = max(int(str(value).replace("SEA", "")) for value in pilot["shop_id"]) + 1

    for _, candidate in qualified.iterrows():
        pilot_index = pilot_by_address.get(candidate["_address_key"])
        if pilot_index is not None:
            source = pilot.loc[pilot_index]
            matched_pilot_indexes.add(pilot_index)
            shop_id = source["shop_id"]
            neighborhood = source["neighborhood"]
            shop_type = source["shop_type"]
        else:
            shop_id = f"SEA{next_id:03d}"
            next_id += 1
            neighborhood = pd.NA
            shop_type = pd.NA

        rows.append(
            {
                "shop_id": shop_id,
                "google_place_id": candidate["place_id"],
                "shop_name": candidate["shop_name"],
                "city": "Seattle",
                "neighborhood": neighborhood,
                "address": candidate["formatted_address"],
                "shop_type": shop_type,
                "google_rating": candidate["google_rating"],
                "google_review_count": candidate["google_review_count"],
                "website_url": candidate["website_url"],
                "google_maps_url": candidate["google_maps_url"],
                "date_collected": str(candidate["date_collected_utc"])[:10],
                "menu_verification_status": "Verified matcha on menu",
            }
        )

    # Keep pilot shops that did not appear in the four API discovery queries.
    for pilot_index, source in pilot.iterrows():
        if pilot_index in matched_pilot_indexes:
            continue
        rows.append(
            {
                "shop_id": source["shop_id"],
                "google_place_id": pilot_place_ids.get(source["shop_id"], pd.NA),
                "shop_name": source["shop_name"],
                "city": source["city"],
                "neighborhood": source["neighborhood"],
                "address": source["address"],
                "shop_type": source["shop_type"],
                "google_rating": source["google_rating"],
                "google_review_count": source["google_review_count"],
                "website_url": source["website_url"],
                "google_maps_url": source["google_maps_url"],
                "date_collected": pd.to_datetime(source["date_collected"]).date().isoformat(),
                "menu_verification_status": "Verified in pilot",
            }
        )

    master = pd.DataFrame(rows)
    mapped_neighborhoods = master["shop_id"].map(NEIGHBORHOOD_BY_SHOP_ID)
    master["neighborhood"] = master["neighborhood"].fillna(mapped_neighborhoods)
    mapped_shop_types = master["shop_id"].map(SHOP_TYPE_BY_SHOP_ID)
    master["shop_type"] = master["shop_type"].fillna(mapped_shop_types)
    mapped_addresses = master["shop_id"].map(ADDRESS_BY_SHOP_ID)
    master["address"] = mapped_addresses.fillna(master["address"])
    master["_id_number"] = master["shop_id"].str.replace("SEA", "", regex=False).astype(int)
    master = master.sort_values("_id_number").drop(columns="_id_number")

    if master["shop_id"].duplicated().any():
        raise ValueError("Duplicate shop_id found in shops master")
    duplicate_business_key = (
        master["shop_name"].map(normalize) + "|" + master["address"].map(normalize)
    )
    if duplicate_business_key.duplicated().any():
        raise ValueError("Duplicate normalized shop name and address found in shops master")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    master.to_csv(OUTPUT_PATH, index=False)

    print(f"Pilot shops: {len(pilot)}")
    print(f"Qualified API candidates: {len(qualified)}")
    print(f"Pilot/candidate matches: {len(matched_pilot_indexes)}")
    print(f"Final unique Seattle shops: {len(master)}")
    print(f"New shop IDs assigned: {len(master) - len(pilot)}")
    print(f"Missing neighborhood: {master['neighborhood'].isna().sum()}")
    print(f"Missing shop_type: {master['shop_type'].isna().sum()}")
    print(f"Saved: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
