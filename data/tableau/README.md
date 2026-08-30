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

Only 23 of 28 shops have complete itemized menus. Use `has_complete_menu` when a
visual compares menu variety or prices. Five source-limited shops should remain in
location/coverage views but should not be treated as zero-menu shops.
