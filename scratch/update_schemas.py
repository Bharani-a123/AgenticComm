import json

schemas = {
    "saree": {
        "category": "saree",
        "display_name": "Saree",
        "required_attributes": {
            "material": ["chiffon", "cotton", "georgette", "linen", "silk"],
            "budget_max": "integer"
        },
        "optional_attributes": {
            "color": ["blue", "green", "pink", "red"],
            "occasion": ["casual", "festive", "party", "wedding"]
        }
    },
    "mesh_chair": {
        "category": "mesh_chair",
        "display_name": "Mesh Chair",
        "required_attributes": {
            "usage_hours": [4, 8, 12, 24],
            "budget_max": "integer"
        },
        "optional_attributes": {
            "warranty_years": [1, 2, 3, 5],
            "color": ["black", "blue", "grey", "white"]
        }
    },
    "running_shoes": {
        "category": "running_shoes",
        "display_name": "Running Shoes",
        "required_attributes": {
            "size": [8, 9, 10, 11],
            "budget_max": "integer"
        },
        "optional_attributes": {
            "terrain": ["road", "track", "trail"],
            "cushioning": ["minimal", "neutral", "plush"]
        }
    },
    "smartphone": {
        "category": "smartphone",
        "display_name": "Smartphone",
        "required_attributes": {
            "ram_gb": [4, 8, 12, 16],
            "storage_gb": [64, 128, 256, 512],
            "budget_max": "integer"
        },
        "optional_attributes": {
            "camera_priority": "boolean"
        }
    },
    "backpack": {
        "category": "backpack",
        "display_name": "Backpack",
        "required_attributes": {
            "capacity_liters": [15, 20, 30, 40],
            "laptop_compatible": "boolean",
            "budget_max": "integer"
        },
        "optional_attributes": {
            "water_resistant": "boolean"
        }
    }
}

for cat, data in schemas.items():
    with open(f"app/taxonomy/schemas/{cat}.json", "w") as f:
        json.dump(data, f, indent=2)
