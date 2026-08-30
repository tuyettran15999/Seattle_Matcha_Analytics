# Seattle Matcha Analytics

An end-to-end analytics project for answering:

> Where should a matcha lover go in the Seattle area based on location, price, ratings, and menu variety?

## Scope

- Current release: Seattle
- Planned expansion: Bellevue, Lynnwood, and Federal Way
- Shop discovery and metadata: Google Places API (New)
- Menu data: official shop websites and menus
- Menu structuring: AI-assisted extraction with human validation
- Analysis: Python, SQL, and Tableau

## Current status

- 28 verified Seattle shops
- 23 complete itemized menus and 203 reviewed matcha menu items
- Google Places collection completed for shop metadata
- AI-assisted extraction completed with auditable human overrides
- Analysis-ready CSVs and SQLite database completed
- Current phase: Tableau dashboard

## Project structure

```text
data/raw/        Original pilot files and raw API responses
data/processed/  Cleaned and analysis-ready datasets
data/tableau/    Stable Tableau-ready CSV sources
reports/         Exported SQL results
sql/             Reusable business queries
src/             Reusable collection and transformation code
```

## First Google Places test

1. Enable **Places API (New)** in a Google Cloud project and create an API key.
2. Copy `.env.example` to `.env` and add the key. Never commit `.env`.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run:

```bash
python src/collect_places.py --query "matcha in Seattle, WA" --limit 10
```

The collector saves the untouched JSON response and a flattened candidate CSV in
`data/raw/google_places/`. Candidates still require menu verification before they
are accepted into the final shops dataset.

## AI-assisted menu extraction

The extraction pipeline uses `gpt-5.6-luna` with Structured Outputs. AI output is
validated against a strict schema and remains marked `Needs human review` until it
has been compared with the official menu.

1. Add `OPENAI_API_KEY` to `.env` (never commit this file).
2. Save official menu text as a UTF-8 text file under `data/raw/menu_text_samples/`.
3. Validate inputs without making an API request:

```bash
python src/extract_menu.py \
  --shop-id SEA001 \
  --menu-url "https://official-menu.example" \
  --menu-text-file data/raw/menu_text_samples/sea001_sample.txt \
  --dry-run
```

4. Remove `--dry-run` only after reviewing the input and confirming API usage.

Raw model JSON is saved under `data/raw/ai_menu_extractions/`; flattened review
CSVs are saved under `data/processed/ai_menu_extractions/`.

## Collection methodology

Candidate businesses will be found through multiple product- and location-based
queries to reduce ranking bias from any single search result. A business qualifies
only if it has a physical location in one of the four selected cities and an
officially verifiable matcha-based beverage.

## Analytics outputs

- `data/processed/shops_analytics.csv`
- `data/processed/menu_items_analytics.csv`
- `data/processed/seattle_matcha.db`
- `sql/business_queries.sql`
- `reports/sql_results/`

The current Seattle dataset contains 203 reviewed menu items. Five verified shops
remain in coverage reporting but are excluded from menu-comparison metrics because
their official sources do not publish complete itemized menus.

## Tableau

Run `python src/build_tableau_sources.py`, then follow the relationship model in
`data/tableau/README.md`. Relationships are used instead of physical joins to
prevent duplicated shop-level metrics.
