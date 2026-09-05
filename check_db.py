from app.db.postgres import SessionLocal
from app.db.models import Product
db = SessionLocal()
res = db.query(Product).filter(Product.category == 'saree').all()
matching = [p for p in res if p.normalized.get('material') == 'cotton' and p.normalized.get('color') == 'green']
print('Total green cotton:', len(matching))
print('All sarees count:', len(res))
