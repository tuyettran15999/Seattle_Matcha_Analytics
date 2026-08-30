"""Build the reviewed Seattle matcha menu dataset and update collection status."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from extract_menu import apply_manual_overrides


ROOT = Path(__file__).resolve().parents[1]
PILOT_PATH = ROOT / "data/raw/menu_items_pilot_cleaned.csv"
EXTRACTION_DIR = ROOT / "data/processed/ai_menu_extractions"
OUTPUT_PATH = ROOT / "data/processed/menu_items_seattle_reviewed.csv"
TRACKER_PATH = ROOT / "data/processed/menu_collection_tracker.csv"

PILOT_SHOPS = {"SEA001", "SEA002", "SEA003"}
BLOCKED = {
    "SEA007": "Official site confirms matcha but publishes no itemized menu or prices",
    "SEA011": "Official site confirms matcha but publishes no itemized menu or prices",
    "SEA014": "Official location page is public, but the Pioneer Square itemized menu is unavailable",
    "SEA016": "Official site confirms the Seattle cafe and matcha source, but no cafe menu is published",
    "SEA018": "Official brand site publishes a Tacoma menu, not a verified itemized Seattle menu",
}


def cleaned_pilot() -> pd.DataFrame:
    data = pd.read_csv(PILOT_PATH, keep_default_na=False)
    data = data[data["shop_id"].isin(PILOT_SHOPS)].copy()
    data = data.rename(columns={"matcha_grade_claim": "matcha_type_claim"})
    for column in ["min_price", "max_price"]:
        data[column] = pd.to_numeric(
            data[column].astype(str).str.replace("$", "", regex=False), errors="coerce"
        )
    data["price_is_starting"] = False
    data["extraction_evidence"] = "Human-validated pilot menu record"
    data["review_status"] = "Reviewed"
    return data


def main() -> None:
    frames = [cleaned_pilot()]
    for path in sorted(EXTRACTION_DIR.glob("sea*_menu_items.csv")):
        shop_id = path.stem[:6].upper()
        if shop_id in PILOT_SHOPS:
            continue
        data = apply_manual_overrides(pd.read_csv(path))
        data["review_status"] = "Reviewed"
        data.to_csv(path, index=False)
        frames.append(data)

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined = combined.sort_values(["shop_id", "item_id"], kind="stable")
    combined.to_csv(OUTPUT_PATH, index=False)

    tracker = pd.read_csv(TRACKER_PATH, keep_default_na=False)
    extracted = set(combined["shop_id"])
    for index, row in tracker.iterrows():
        shop_id = row["shop_id"]
        if shop_id in extracted:
            tracker.loc[index, "raw_text_status"] = "Full menu captured"
            tracker.loc[index, "ai_extraction_status"] = (
                "Human-validated pilot" if shop_id in PILOT_SHOPS else "Extracted"
            )
            tracker.loc[index, "human_review_status"] = "Reviewed"
            tracker.loc[index, "output_file"] = str(
                OUTPUT_PATH.relative_to(ROOT)
                if shop_id in PILOT_SHOPS
                else Path("data/processed/ai_menu_extractions")
                / f"{shop_id.lower()}_menu_items.csv"
            )
        elif shop_id in BLOCKED:
            tracker.loc[index, "menu_source_status"] = "Unavailable"
            tracker.loc[index, "raw_text_status"] = "Blocked"
            tracker.loc[index, "ai_extraction_status"] = "Not applicable"
            tracker.loc[index, "human_review_status"] = "Reviewed limitation"
            tracker.loc[index, "notes"] = BLOCKED[shop_id]
    tracker.to_csv(TRACKER_PATH, index=False)

    print(f"Wrote {len(combined)} reviewed menu items from {len(extracted)} shops")
    print(f"Documented {len(BLOCKED)} source-limited shops")


if __name__ == "__main__":
    main()
