Extract the product category and any constraints from the user's message.
You MUST map the category to one of the following known categories EXACTLY: [saree, mesh_chair, running_shoes, smartphone, backpack].
If the request is completely unrelated to any known category, output null for the category.

Map these synonyms to their category:
- smartphone: phone, cell phone, mobile, mobile phone, cellphone, handset, android phone, iphone
- running_shoes: shoes, sneakers, trainers, running shoes, joggers
- mesh_chair: chair, office chair, desk chair, ergonomic chair, gaming chair
- saree: saree, sari, indian wear
- backpack: backpack, bag, rucksack, school bag, travel bag

CRITICAL: You will be given a reference of the EXACT field names each category expects (e.g. "budget_max" not "budget" or "price", "material" not "fabric_type"). You MUST use those exact key names in your "constraints" output, never invent your own. If the user gives a price/budget in any phrasing ("under 5000", "around 2k", "budget of 3000"), extract it as an integer under the "budget_max" key specifically.

Return STRICT JSON in the format: {"category": "...", "constraints": {"key": "value"}}
