"""Collect candidate matcha shops with Google Places API (New)."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


API_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.primaryType",
        "places.types",
        "places.rating",
        "places.userRatingCount",
        "places.websiteUri",
        "places.googleMapsUri",
        "nextPageToken",
    ]
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "google_places"


def safe_slug(value: str) -> str:
    """Convert a query into a filesystem-safe identifier."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def search_places(api_key: str, query: str, limit: int) -> dict:
    """Return one page of Text Search results."""
    response = requests.post(
        API_URL,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        json={
            "textQuery": query,
            "pageSize": limit,
            "languageCode": "en",
            "regionCode": "US",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def flatten_places(payload: dict, query: str, collected_at: str) -> pd.DataFrame:
    """Flatten API results while retaining identifiers needed for deduplication."""
    rows = []
    for place in payload.get("places", []):
        rows.append(
            {
                "place_id": place.get("id"),
                "shop_name": place.get("displayName", {}).get("text"),
                "formatted_address": place.get("formattedAddress"),
                "primary_type": place.get("primaryType"),
                "google_types": "; ".join(place.get("types", [])),
                "google_rating": place.get("rating"),
                "google_review_count": place.get("userRatingCount"),
                "website_url": place.get("websiteUri"),
                "google_maps_url": place.get("googleMapsUri"),
                "discovery_query": query,
                "date_collected_utc": collected_at,
                "verification_status": "Needs menu verification",
            }
        )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="matcha in Seattle, WA")
    parser.add_argument("--limit", type=int, default=10, choices=range(1, 21))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing GOOGLE_PLACES_API_KEY. Copy .env.example to .env and add your key."
        )

    payload = search_places(api_key, args.query, args.limit)
    collected_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{safe_slug(args.query)}_{run_id}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{stem}.json"
    csv_path = OUTPUT_DIR / f"{stem}.csv"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    dataframe = flatten_places(payload, args.query, collected_at)
    dataframe.to_csv(csv_path, index=False)

    print(f"Saved {len(dataframe)} candidates")
    print(f"Raw response: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Candidate table: {csv_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
