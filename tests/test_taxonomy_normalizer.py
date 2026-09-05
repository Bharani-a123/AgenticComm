import pytest
from app.protocols.acp.normalizer import normalize

def test_saree_normalization_across_all_merchants():
    """Proves all three merchants converge to the exact same canonical schema for Sarees."""
    # Given raw data from 3 different merchants
    merchant_a_raw = {"fabric_type": "silk", "max_price": 5000, "fabric_color": "red", "event": "wedding", "unknown_tag": "drop_me"}
    merchant_b_raw = {"material": "silk", "price_cap": 5000, "hue": "red", "use_case": "wedding"}
    merchant_c_raw = {"fabric": "silk", "budget": 5000, "shade": "red", "wear_type": "wedding", "internal_id": "123"}

    # When normalized
    norm_a = normalize("Merchant A", "saree", merchant_a_raw)
    norm_b = normalize("Merchant B", "saree", merchant_b_raw)
    norm_c = normalize("Merchant C", "saree", merchant_c_raw)

    expected = {
        "material": "silk",
        "budget_max": 5000,
        "color": "red",
        "occasion": "wedding"
    }

    # Then they must perfectly match the expected canonical schema
    assert norm_a == expected
    assert norm_b == expected
    assert norm_c == expected

def test_unmapped_fields_are_dropped():
    """Proves that unexpected merchant fields do not bleed into our canonical system."""
    raw = {"fabric_type": "cotton", "garbage_key": "garbage_value"}
    norm = normalize("Merchant A", "saree", raw)
    
    assert "material" in norm
    assert norm["material"] == "cotton"
    assert "garbage_key" not in norm # Dropped cleanly

def test_unknown_merchant_or_category_returns_empty():
    """Proves safe fallback for unknown configurations."""
    assert normalize("Merchant Unknown", "saree", {"fabric_type": "silk"}) == {}
    assert normalize("Merchant A", "unknown_category", {"fabric_type": "silk"}) == {}
