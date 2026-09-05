from sqlalchemy import create_engine
from app.db.postgres import SessionLocal
from app.db.models import IntentMandate
db = SessionLocal()
latest = db.query(IntentMandate).order_by(IntentMandate.created_at.desc()).first()
print('Constraints:', latest.constraints)

