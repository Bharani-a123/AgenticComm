import os
import json
from collections import defaultdict
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url)

categories = ['saree', 'mesh_chair', 'running_shoes', 'smartphone', 'backpack']

for cat in categories:
    print(f"\n========== {cat.upper()} ==========")
    with engine.connect() as conn:
        res = conn.execute(text(f"SELECT raw_attributes, normalized FROM products WHERE category = '{cat}'")).fetchall()
    
    normalized_keys = defaultdict(set)
    raw_keys_all = set()
    
    for row in res:
        raw = row[0] or {}
        norm = row[1] or {}
        
        for k in raw.keys():
            raw_keys_all.add(k)
            
        for k, v in norm.items():
            if isinstance(v, list):
                for item in v:
                    normalized_keys[k].add(str(item))
            elif isinstance(v, bool):
                normalized_keys[k].add(str(v))
            else:
                normalized_keys[k].add(str(v))
                
    print("NORMALIZED KEYS & VALUES:")
    for k, v in normalized_keys.items():
        if len(v) < 15:
            print(f"  - {k}: {v}")
        else:
            v_list = list(v)
            try:
                numeric = sorted([float(x) for x in v])
                print(f"  - {k}: [min={numeric[0]}, max={numeric[-1]}]")
            except:
                print(f"  - {k}: [{len(v)} distinct values, e.g. {v_list[:5]}...]")
            
    print("\nRAW KEYS TOTAL:", raw_keys_all)
    
    missing_from_norm = raw_keys_all - set(normalized_keys.keys())
    print("\nKEYS IN RAW BUT MISSING FROM NORMALIZED (Potentially unmapped):", missing_from_norm)
