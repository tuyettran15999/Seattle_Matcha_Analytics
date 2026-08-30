"""Resolve Google Place IDs for pilot shops missing from discovery results."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


API_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = "places.id,places.displayName,places.formattedAddress"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "pilot_place_id_lookup.csv"

PILOT_LOOKUPS = [
    {
        "shop_id": "SEA002",
        "query": "The Moo Bar, 2124 Westlake Ave N, Seattle, WA 98121",
    },
    {
        "shop_id": "SEA003",
        "query": "Hey Tea, 910 John St, Seattle, WA 98109",
    },
    {
        "shop_id": "SEA005",
        "query": "Drip Drip Coffeehouse, 355 15th Ave, Seattle, WA 98122",
    },
]


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise SystemExit("Missing GOOGLE_PLACES_API_KEY in .env")

    rows = []
    for lookup in PILOT_LOOKUPS:
        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            json={
                "textQuery": lookup["query"],
                "pageSize": 1,
                "languageCode": "en",
                "regionCode": "US",
            },
            timeout=30,
        )
        response.raise_for_status()
        places = response.json().get("places", [])
        place = places[0] if places else {}
        rows.append(
            {
                "shop_id": lookup["shop_id"],
                "lookup_query": lookup["query"],
                "google_place_id": place.get("id"),
                "returned_name": place.get("displayName", {}).get("text"),
                "returned_address": place.get("formattedAddress"),
            }
        )

    output = pd.DataFrame(rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_PATH, index=False)
    print(output.to_string(index=False))
    print(f"Saved: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
