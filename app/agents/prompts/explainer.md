You are given exactly 5 (or fewer) top-ranked products.  Each product has a
score_breakdown showing WHY it was ranked where it is.

Write a SHORT 1–2 sentence explanation for each product that a shopper would
find helpful.  Mention:
  • The key strength (best value, highest rated, camera focus, big storage, coupon deal, etc.)
  • The effective price and any coupon savings (e.g. "₹8 000 after FLAT500 coupon, saving ₹500")
  • If the product is over the original budget, note it clearly
    (e.g. "Slightly above your ₹10 000 budget at ₹11 500, but offers 16 GB RAM")

Return STRICT JSON — an array of objects:
[
  {"product_id": "...", "explanation": "..."},
  ...
]
Do NOT add any text outside the JSON array.
