import uuid
import random
from app.db.postgres import SessionLocal
from app.db.models import Merchant, Product, Coupon
from app.protocols.acp.normalizer import normalize

MERCHANT_NAMES = ["Merchant A", "Merchant B", "Merchant C"]
CATEGORIES = ["saree", "mesh_chair", "running_shoes", "smartphone", "backpack"]

def seed_db():
    session = SessionLocal()
    
    # 1. Create Merchants (Idempotent)
    merchants = {}
    for name in MERCHANT_NAMES:
        m = session.query(Merchant).filter_by(name=name).first()
        if not m:
            m = Merchant(name=name, raw_schema_notes={"info": f"Uses proprietary field names for {name}"})
            session.add(m)
            session.commit()
            session.refresh(m)
        merchants[name] = m

    # 2. Create Products (Idempotent 20 per category per merchant)
    for name, merchant in merchants.items():
        for category in CATEGORIES:
            existing = session.query(Product).filter_by(merchant_id=merchant.merchant_id, category=category).count()
            if existing >= 20:
                continue

            for i in range(20 - existing):
                sku = f"{name.split()[1]}-{category[:3].upper()}-{i}-{uuid.uuid4().hex[:6]}"
                
                # Mock raw attributes using the EXACT weird keys from our normalizer.py
                raw_attrs = {}
                price = round(random.uniform(500, 15000), 2)
                
                if category == "saree":
                    materials = ["silk", "cotton", "georgette", "chiffon", "linen"]
                    colors = ["red", "blue", "green", "pink"]
                    occasions = ["wedding", "casual", "party", "festive"]
                    
                    # Force some specific test cases the user checks often
                    if i == 0:
                        chosen_mat = "georgette"
                        chosen_col = "blue"
                        chosen_occ = "festive"
                        price = 2500.00
                    elif i == 1:
                        chosen_mat = "cotton"
                        chosen_col = "pink"
                        chosen_occ = "festive"
                        price = 8500.00
                    else:
                        chosen_mat = random.choice(materials)
                        chosen_col = random.choice(colors)
                        chosen_occ = random.choice(occasions)

                    if name == "Merchant A":
                        raw_attrs = {"fabric_type": chosen_mat, "max_price": price, "fabric_color": chosen_col, "event": chosen_occ}
                    elif name == "Merchant B":
                        raw_attrs = {"material": chosen_mat, "price_cap": price, "hue": chosen_col, "use_case": chosen_occ}
                    elif name == "Merchant C":
                        raw_attrs = {"fabric": chosen_mat, "budget": price, "shade": chosen_col, "wear_type": chosen_occ}
                elif category == "mesh_chair":
                    usage = [4, 8, 12, 24]
                    colors = ["black", "grey", "blue", "white"]
                    warranties = [1, 2, 3, 5]
                    if name == "Merchant A":
                        raw_attrs = {"use_hrs": random.choice(usage), "max_inr": price, "warranty": random.choice(warranties), "chair_color": random.choice(colors), "unmapped_mesh1": "val1"}
                    elif name == "Merchant B":
                        raw_attrs = {"usage_time": random.choice(usage), "price_limit": price, "yr_warranty": random.choice(warranties), "shade": random.choice(colors), "unmapped_mesh2": "val2"}
                    elif name == "Merchant C":
                        raw_attrs = {"daily_hours": random.choice(usage), "budget": price, "guarantee": random.choice(warranties), "colour": random.choice(colors)}
                elif category == "running_shoes":
                    sizes = [8, 9, 10, 11]
                    terrains = ["road", "trail", "track"]
                    cushioning = ["neutral", "plush", "minimal"]
                    if name == "Merchant A":
                        raw_attrs = {"shoe_size": random.choice(sizes), "max_price": price, "surface": random.choice(terrains), "softness": random.choice(cushioning)}
                    elif name == "Merchant B":
                        raw_attrs = {"foot_size": random.choice(sizes), "price_cap": price, "ground_type": random.choice(terrains), "padding": random.choice(cushioning)}
                    elif name == "Merchant C":
                        raw_attrs = {"size_us": random.choice(sizes), "budget": price, "use_case": random.choice(terrains), "feel": random.choice(cushioning), "unmapped_shoes": 123}
                elif category == "smartphone":
                    rams = [4, 8, 12, 16]
                    storages = [64, 128, 256, 512]
                    cam_pri = [True, False]
                    if name == "Merchant A":
                        raw_attrs = {"memory_gb": random.choice(rams), "max_price": price, "disk_gb": random.choice(storages), "is_cam_focus": random.choice(cam_pri)}
                    elif name == "Merchant B":
                        raw_attrs = {"ram": random.choice(rams), "price_cap": price, "storage": random.choice(storages), "cam_centric": random.choice(cam_pri)}
                    elif name == "Merchant C":
                        raw_attrs = {"ram_capacity": random.choice(rams), "budget": price, "rom_capacity": random.choice(storages), "good_camera": random.choice(cam_pri), "unmapped_phone": "yes"}
                elif category == "backpack":
                    vols = [15, 20, 30, 40]
                    lap = [True, False]
                    wat = [True, False]
                    if name == "Merchant A":
                        raw_attrs = {"volume_l": random.choice(vols), "max_price": price, "fits_laptop": random.choice(lap), "waterproof": random.choice(wat)}
                    elif name == "Merchant B":
                        raw_attrs = {"capacity": random.choice(vols), "price_cap": price, "laptop_sleeve": random.choice(lap), "rain_cover": random.choice(wat)}
                    elif name == "Merchant C":
                        raw_attrs = {"liters": random.choice(vols), "budget": price, "pc_friendly": random.choice(lap), "repels_water": random.choice(wat)}
                
                # 3. IMMEDIATELY NORMALIZE
                normalized_attrs = normalize(name, category, raw_attrs)
                
                p = Product(
                    merchant_id=merchant.merchant_id,
                    merchant_sku=sku,
                    category=category,
                    raw_attributes=raw_attrs,
                    normalized=normalized_attrs,
                    price=price,
                    stock=True if i in [0, 1] else random.choices([True, False], weights=[90, 10])[0], # 90% in stock, force 0 and 1
                    rating=round(random.uniform(3.5, 5.0), 1)
                )
                session.add(p)
    
    # 4. Create Coupons
    from datetime import datetime, timedelta, timezone
    valid_until_date = datetime.now(timezone.utc) + timedelta(days=60)

    for name, merchant in merchants.items():
        existing = session.query(Coupon).filter_by(merchant_id=merchant.merchant_id).count()
        if existing == 0:
            c1 = Coupon(merchant_id=merchant.merchant_id, code="FLAT500", discount_type="flat", discount_value=500.0, min_order_value=2000, valid_until=valid_until_date)
            c2 = Coupon(merchant_id=merchant.merchant_id, code="SAVE10", discount_type="percentage", discount_value=10.0, max_discount_cap=1000, min_order_value=1500, valid_until=valid_until_date)
            session.add_all([c1, c2])

    session.commit()
    
    # 5. Print Summary
    m_count = session.query(Merchant).count()
    p_count = session.query(Product).count()
    c_count = session.query(Coupon).count()
    print(f"✅ Seeding Complete!")
    print(f"🏢 Merchants: {m_count}")
    print(f"📦 Products:  {p_count} (Raw & Normalized generated)")
    print(f"🎟️ Coupons:   {c_count}")
    
if __name__ == "__main__":
    seed_db()
