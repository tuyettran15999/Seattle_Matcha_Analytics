# Data folders

## `raw/` — canonical inputs and source evidence

- `menu_items_verified_source.xlsx`: the only menu workbook edited manually.
- `google_places/`: untouched API responses and flattened discovery files.
- `menu_text_samples/`: official menu text supplied to the extraction model.
- `ai_menu_extractions/`: raw JSON model responses retained for auditability.
- Candidate qualification, exclusion, override, and Place ID lookup files.

## `archive/` — completed pilot material

Historical pilot work retained for provenance. It is not used when the verified
menu source workbook is available.

## `interim/` — reproducible cleaning-stage outputs

- `shop_candidates_merged.csv`
- `shops_clean.csv`
- `menu_items_clean.csv`
- `menu_collection_tracker.csv`
- `ai_menu_extractions/`: flattened model outputs used during review.

Do not edit these files manually; rebuild them from source data.

## `processed/` — final analysis-ready outputs

- `shops_analytics.csv`
- `menu_items_analytics.csv`
- `data_quality_report.csv`
- `analytics_metadata.json`
- `seattle_matcha.db`

## `tableau/` — stable Tableau inputs

- `shops_dashboard.csv`
- `menu_items_dashboard.csv`
- `menu_item_flavors_dashboard.csv`

Use Tableau relationships as documented in `tableau/README.md`.
