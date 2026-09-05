import json
import os

schema_dir = "app/taxonomy/schemas"
categories = ["saree", "mesh_chair", "running_shoes", "smartphone", "backpack"]

for cat in categories:
    filepath = os.path.join(schema_dir, f"{cat}.json")
    with open(filepath, "r") as f:
        data = json.load(f)
    
    # Move all optional attributes to required
    optional_attrs = data.get("optional_attributes", {})
    required_attrs = data.get("required_attributes", {})
    
    for k, v in optional_attrs.items():
        required_attrs[k] = v
        
    data["required_attributes"] = required_attrs
    data["optional_attributes"] = {}
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

print("Successfully moved all optional attributes to required.")
