import uuid
import random
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://admin:admin@postgres:5432/agentic_commerce"

# We must map port 5432 to localhost to run it outside docker. Wait, the docker compose exposes 5432? Yes, 5432/tcp -> 5432.
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def update_product_names():
    from sqlalchemy import text
    session = Session()
    result = session.execute(text("SELECT product_id, category, normalized FROM products")).fetchall()
    
    brand_models = {
        "smartphone": [
            ("Samsung", "Galaxy S24"), ("Apple", "iPhone 15"), ("Google", "Pixel 8"),
            ("OnePlus", "12"), ("Xiaomi", "14 Pro"), ("Motorola", "Edge 50"),
            ("Vivo", "X100"), ("Oppo", "Find X7"), ("Realme", "GT 5"), ("Asus", "ROG 8")
        ],
        "saree": [
            ("Nalli", "Kanjivaram Silk"), ("FabIndia", "Banarasi Georgette"),
            ("Meena Bazaar", "Mysore Silk"), ("Kalanikethan", "Chanderi Cotton"),
            ("Pothys", "Patola Silk"), ("Chennai Silks", "Bandhani Saree"),
            ("Kalanjali", "Tussar Silk"), ("Kalamandir", "Organza Saree")
        ],
        "mesh_chair": [
            ("Herman Miller", "Aeron"), ("Steelcase", "Leap V2"),
            ("ErgoTune", "Supreme"), ("Sihoo", "M57"),
            ("Ticova", "Ergonomic"), ("Branch", "Ergonomic Chair"),
            ("IKEA", "Markus"), ("Secretlab", "NeueChair")
        ],
        "backpack": [
            ("North Face", "Borealis"), ("Osprey", "Farpoint"),
            ("Samsonite", "Tectonic"), ("Patagonia", "Refugio"),
            ("JanSport", "Right Pack"), ("Thule", "Crossover"),
            ("Timbuk2", "Authority"), ("Aer", "City Pack")
        ],
        "running_shoes": [
            ("Nike", "Pegasus 40"), ("Adidas", "Ultraboost 1.0"),
            ("Brooks", "Ghost 15"), ("Asics", "Gel-Kayano 30"),
            ("Hoka", "Clifton 9"), ("New Balance", "1080v13"),
            ("Saucony", "Ride 17"), ("Puma", "Velocity Nitro")
        ]
    }
    
    updates = 0
    for row in result:
        pid, cat, norm = row
        brand, model = random.choice(brand_models.get(cat, [("Generic", "Model")]))
        
        # Append some specs to make it unique and informative
        specs = []
        if cat == "smartphone":
            if norm.get("ram_gb"): specs.append(f"{norm['ram_gb']}GB RAM")
            if norm.get("storage_gb"): specs.append(f"{norm['storage_gb']}GB")
        elif cat == "running_shoes":
            if norm.get("size"): specs.append(f"Size {norm['size']}")
        elif cat == "mesh_chair":
            if norm.get("color"): specs.append(norm['color'].title())
        elif cat == "saree":
            if norm.get("color"): specs.append(norm['color'].title())
        elif cat == "backpack":
            if norm.get("capacity_liters"): specs.append(f"{norm['capacity_liters']}L")
            
        name = f"{brand} {model}"
        if specs:
            name += f" ({', '.join(specs)})"
            
        norm["product_name"] = name
        
        session.execute(
            text("UPDATE products SET normalized = :norm WHERE product_id = :pid"),
            {"norm": json.dumps(norm), "pid": pid}
        )
        updates += 1
        
    session.commit()
    print(f"Updated {updates} products with realistic names!")

if __name__ == "__main__":
    update_product_names()
