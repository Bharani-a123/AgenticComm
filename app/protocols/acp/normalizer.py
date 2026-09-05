import logging

logger = logging.getLogger(__name__)

# The 15 Explicit Mappings: 3 Merchants x 5 Categories
MAPPINGS = {
    # 1. Saree
    ("Merchant A", "saree"): {"fabric_type": "material", "max_price": "budget_max", "fabric_color": "color", "event": "occasion"},
    ("Merchant B", "saree"): {"material": "material", "price_cap": "budget_max", "hue": "color", "use_case": "occasion"},
    ("Merchant C", "saree"): {"fabric": "material", "budget": "budget_max", "shade": "color", "wear_type": "occasion"},
    
    # 2. Mesh Chair
    ("Merchant A", "mesh_chair"): {"use_hrs": "usage_hours", "max_inr": "budget_max", "warranty": "warranty_years", "chair_color": "color"},
    ("Merchant B", "mesh_chair"): {"usage_time": "usage_hours", "price_limit": "budget_max", "yr_warranty": "warranty_years", "shade": "color"},
    ("Merchant C", "mesh_chair"): {"daily_hours": "usage_hours", "budget": "budget_max", "guarantee": "warranty_years", "colour": "color"},
    
    # 3. Running Shoes
    ("Merchant A", "running_shoes"): {"shoe_size": "size", "max_price": "budget_max", "surface": "terrain", "softness": "cushioning"},
    ("Merchant B", "running_shoes"): {"foot_size": "size", "price_cap": "budget_max", "ground_type": "terrain", "padding": "cushioning"},
    ("Merchant C", "running_shoes"): {"size_us": "size", "budget": "budget_max", "use_case": "terrain", "feel": "cushioning"},
    
    # 4. Smartphone
    ("Merchant A", "smartphone"): {"memory_gb": "ram_gb", "max_price": "budget_max", "disk_gb": "storage_gb", "is_cam_focus": "camera_priority"},
    ("Merchant B", "smartphone"): {"ram": "ram_gb", "price_cap": "budget_max", "storage": "storage_gb", "cam_centric": "camera_priority"},
    ("Merchant C", "smartphone"): {"ram_capacity": "ram_gb", "budget": "budget_max", "rom_capacity": "storage_gb", "good_camera": "camera_priority"},
    
    # 5. Backpack
    ("Merchant A", "backpack"): {"volume_l": "capacity_liters", "max_price": "budget_max", "fits_laptop": "laptop_compatible", "waterproof": "water_resistant"},
    ("Merchant B", "backpack"): {"capacity": "capacity_liters", "price_cap": "budget_max", "laptop_sleeve": "laptop_compatible", "rain_cover": "water_resistant"},
    ("Merchant C", "backpack"): {"liters": "capacity_liters", "budget": "budget_max", "pc_friendly": "laptop_compatible", "repels_water": "water_resistant"},
}

def normalize(merchant_name: str, category: str, raw_attributes: dict) -> dict:
    """
    Translates raw merchant API attributes into the canonical platform schema.
    Pure function: no DB calls, no LLMs. Unmapped fields are safely dropped.
    """
    mapping = MAPPINGS.get((merchant_name, category), {})
    normalized = {}
    
    for raw_k, raw_v in raw_attributes.items():
        if raw_k in mapping:
            normalized[mapping[raw_k]] = raw_v
        else:
            logger.warning(f"Normalizer dropped unmapped field '{raw_k}' for {merchant_name} -> {category}")
            
    return normalized
