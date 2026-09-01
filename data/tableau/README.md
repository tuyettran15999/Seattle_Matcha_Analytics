# Tableau data model

Use relationships rather than physical joins:

```text
shops_dashboard
  shop_id (one)
      |
      | 1 : many
      v
menu_items_dashboard
  shop_id (many)
  item_id (one)
      |
      | 1 : many
      v
menu_item_flavors_dashboard
  item_id (many)
```

Relationship settings:

1. `shops_dashboard.shop_id = menu_items_dashboard.shop_id`
2. `menu_items_dashboard.item_id = menu_item_flavors_dashboard.item_id`

Do not physically join these files. A physical join would repeat shop metrics for
every menu item and can inflate shop counts, ratings, and review counts.

## Recommended dashboard filters

- `neighborhood`
- `shop_type`
- `matcha_price_level`
- `drink_category`
- `flavor`
- `available_hot`
- `available_iced`

## Recommended KPI fields

- Shops: `COUNTD(shop_id)`
- Menu items: `COUNTD(item_id)`
- Average shop price: `AVG(avg_matcha_price)` from `shops_dashboard`
- Average rating: `AVG(google_rating)` from `shops_dashboard`
- Menu variety: `menu_item_count`
- Flavor variety: `unique_flavor_count`

All 28 shops currently have human-validated, complete itemized menus and price
coverage. Keep `has_complete_menu` in the model so future geographic expansions
can distinguish complete menus from source-limited shops.

## Dynamic Top 5 leaderboard

`matcha_score_rank` is the fixed Seattle-wide rank exported for SQL reporting.
For an interactive Tableau leaderboard that recalculates after area, shop type,
or price-level filters, sort `Shop Name` descending by `AVG(matcha_score)` and use
this table-calculation filter:

```tableau
// Keep Top 5
INDEX() <= 5
```

Filter the calculation to `True` and compute it using `Table (Down)` / `Shop
Name`. Do not place `Neighborhood` on Marks → Detail because it partitions the
table calculation and restarts `INDEX()` for each neighborhood. Use
`ATTR(Neighborhood)` on Tooltip instead.
