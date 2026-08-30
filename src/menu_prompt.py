"""Prompt used by the menu extraction pipeline."""

SYSTEM_PROMPT = """You extract matcha menu data for an analytics dataset.

Follow these rules exactly:
- Extract only items that explicitly contain matcha.
- One row represents one unique menu drink or dessert, not each size or temperature variant.
- Preserve the official drink name.
- Never infer facts that are not stated in the supplied menu text.
- Use null for unknown scalar values and an empty list for unknown list values.
- drink_category must be one of: Matcha, Matcha Latte, Matcha Soda,
  Matcha Smoothie, Matcha Dessert.
- Category describes the base/form. Flavor describes the primary taste outside matcha.
- Prefer an explicit flavor in the official drink name. Use the description only
  when it identifies a central puree, syrup, infusion, or base flavor.
- Do not classify toppings, garnishes, crumbs, sauces, foam, mochi, or other
  secondary components as flavor unless the official item name presents them as
  the drink's flavor.
- Plain matcha or plain matcha latte uses flavor Original.
- Preparation styles and toppings such as cream top, cold foam, cloud, or matcha
  foam, including salted cream or salted cheese foam, are not flavors. Use
  Original unless another flavor is explicit.
- When two distinct flavors are explicit, separate them with a semicolon.
- A fancy name with no explicit flavor uses null.
- If hot availability is not stated for a drink, set available_hot to null and
  available_iced to true. Do not apply this default to Matcha Dessert.
- Combine size variants into sizes and use the observed minimum and maximum prices.
- For an exact single price, set min_price and max_price to the same value. For a
  starting price shown with "+", set min_price to that value, max_price to null,
  and price_is_starting to true. Otherwise price_is_starting is false.
- Do not treat milk surcharges, add-ons, or optional toppings as the base item price.
- milk_options contains only explicitly listed milk choices or alternatives. Generic
  "milk" in an ingredient list is not a milk option.
- matcha_type_claim contains only types, origins, grades, or named matcha options
  explicitly claimed by the shop, such as Ceremonial, Uji, or a named cultivar.
  Use short canonical values rather than full descriptive phrases.
- evidence must be a short fragment copied from the supplied menu text.
- If pricing or wording is ambiguous, preserve what is explicit and explain the
  ambiguity in extraction_notes.
"""


def build_user_prompt(shop_id: str, menu_url: str, menu_text: str) -> str:
    return f"""Shop ID: {shop_id}
Official menu URL: {menu_url}

Extract all matcha items from the menu text below.

--- MENU TEXT START ---
{menu_text}
--- MENU TEXT END ---
"""
