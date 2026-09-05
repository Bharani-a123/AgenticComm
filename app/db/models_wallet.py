import uuid
from sqlalchemy import Column, String, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.db.models import Base

class UserWallet(Base):
    __tablename__ = 'user_wallets'
    user_id = Column(String, primary_key=True)
    allocated_budget = Column(Numeric(15, 2), nullable=False, default=0.0)
