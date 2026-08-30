-- 1. Portfolio-level KPI overview
SELECT
    COUNT(*) AS total_shops,
    SUM(has_complete_menu) AS shops_with_complete_menu,
    SUM(avg_matcha_price IS NOT NULL) AS shops_with_price_data,
    ROUND(AVG(avg_matcha_price), 2) AS avg_shop_matcha_price,
    SUM(menu_item_count) AS total_menu_items
FROM shops;

-- 2. Shops with the widest verified matcha menus
SELECT
    shop_id,
    shop_name,
    neighborhood,
    shop_type,
    menu_item_count,
    unique_flavor_count,
    ROUND(avg_matcha_price, 2) AS avg_matcha_price,
    google_rating
FROM shops
WHERE has_complete_menu = 1
ORDER BY menu_item_count DESC, unique_flavor_count DESC, shop_name
LIMIT 10;

-- 3. Most common explicitly identified flavors
SELECT
    f.flavor,
    COUNT(DISTINCT f.item_id) AS menu_item_count,
    COUNT(DISTINCT f.shop_id) AS shop_count
FROM menu_item_flavors AS f
WHERE LOWER(f.flavor) <> 'original'
GROUP BY f.flavor
ORDER BY shop_count DESC, menu_item_count DESC, f.flavor
LIMIT 15;

-- 4. Matcha menu composition by drink category
SELECT
    drink_category,
    COUNT(*) AS menu_item_count,
    COUNT(DISTINCT shop_id) AS shop_count,
    ROUND(AVG(analytics_price), 2) AS avg_price
FROM menu_items
GROUP BY drink_category
ORDER BY menu_item_count DESC;

-- 5. Price and menu variety by business type
SELECT
    shop_type,
    COUNT(*) AS shop_count,
    SUM(has_complete_menu) AS complete_menu_count,
    ROUND(AVG(avg_matcha_price), 2) AS avg_matcha_price,
    ROUND(AVG(menu_item_count), 1) AS avg_menu_items,
    ROUND(AVG(unique_flavor_count), 1) AS avg_unique_flavors
FROM shops
GROUP BY shop_type
ORDER BY avg_menu_items DESC;

-- 6. Neighborhood coverage and average rating
SELECT
    neighborhood,
    COUNT(*) AS shop_count,
    ROUND(AVG(google_rating), 2) AS avg_google_rating,
    SUM(menu_item_count) AS verified_menu_items
FROM shops
GROUP BY neighborhood
ORDER BY shop_count DESC, verified_menu_items DESC, neighborhood;

-- 7. Balanced recommendation score using only observed, comparable fields
WITH eligible AS (
    SELECT *
    FROM shops
    WHERE has_complete_menu = 1
      AND avg_matcha_price IS NOT NULL
      AND google_rating IS NOT NULL
      AND google_review_count IS NOT NULL
), normalized AS (
    SELECT
        *,
        (google_rating - MIN(google_rating) OVER ()) /
            NULLIF(MAX(google_rating) OVER () - MIN(google_rating) OVER (), 0) AS rating_score,
        (LOG(google_review_count + 1) - MIN(LOG(google_review_count + 1)) OVER ()) /
            NULLIF(MAX(LOG(google_review_count + 1)) OVER () - MIN(LOG(google_review_count + 1)) OVER (), 0) AS popularity_score,
        (menu_item_count - MIN(menu_item_count) OVER ()) * 1.0 /
            NULLIF(MAX(menu_item_count) OVER () - MIN(menu_item_count) OVER (), 0) AS variety_score,
        1 - ((avg_matcha_price - MIN(avg_matcha_price) OVER ()) /
            NULLIF(MAX(avg_matcha_price) OVER () - MIN(avg_matcha_price) OVER (), 0)) AS affordability_score
    FROM eligible
)
SELECT
    shop_id,
    shop_name,
    neighborhood,
    ROUND(google_rating, 1) AS google_rating,
    google_review_count,
    menu_item_count,
    ROUND(avg_matcha_price, 2) AS avg_matcha_price,
    ROUND(
        100 * (
            0.35 * rating_score +
            0.20 * popularity_score +
            0.30 * variety_score +
            0.15 * affordability_score
        ),
        1
    ) AS matcha_score
FROM normalized
ORDER BY matcha_score DESC, shop_name
LIMIT 10;

-- 8. Data coverage audit by shop
SELECT
    shop_id,
    shop_name,
    has_complete_menu,
    menu_item_count,
    price_coverage_pct,
    raw_text_status,
    human_review_status
FROM shops
ORDER BY has_complete_menu, price_coverage_pct, shop_name;
