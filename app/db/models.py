import uuid
from datetime import datetime
from sqlalchemy import String, Numeric, Boolean, ForeignKey, CheckConstraint, text, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()

class Merchant(Base):
    __tablename__ = 'merchants'
    merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=True)
    raw_schema_notes: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"))

class Product(Base):
    __tablename__ = 'products'
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('merchants.merchant_id'), nullable=False)
    merchant_sku: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, index=True, nullable=False)
    raw_attributes: Mapped[dict] = mapped_column(JSONB, nullable=False) # Untouched merchant API output
    normalized: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, server_default="INR", nullable=False)
    stock: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    rating: Mapped[float] = mapped_column(Numeric(2, 1), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"))

    __table_args__ = (Index('ix_merchant_sku', 'merchant_id', 'merchant_sku', unique=True),)

class Coupon(Base):
    __tablename__ = 'coupons'
    coupon_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('merchants.merchant_id'), nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    discount_type: Mapped[str] = mapped_column(String, nullable=False)
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    applicable_category: Mapped[str] = mapped_column(String, nullable=True)
    min_order_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, server_default=text("0.0"))
    max_discount_cap: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        CheckConstraint("discount_type IN ('flat', 'percentage')", name='check_discount_type'),
        Index('ix_merchant_coupon', 'merchant_id', 'code', unique=True),
    )

class UserPaymentMethod(Base):
    __tablename__ = 'user_payment_methods'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    razorpay_customer_id: Mapped[str] = mapped_column(String, nullable=True)
    razorpay_token_id: Mapped[str] = mapped_column(String, nullable=False)
    method_type: Mapped[str] = mapped_column(String, nullable=False) # 'card' or 'upi'
    last_four: Mapped[str] = mapped_column(String, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"))

class IntentMandate(Base):
    __tablename__ = 'intent_mandates'
    mandate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    constraints: Mapped[dict] = mapped_column(JSONB, nullable=False)
    completeness: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"))

class CartMandate(Base):
    __tablename__ = 'cart_mandates'
    mandate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    intent_mandate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('intent_mandates.mandate_id'), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('products.product_id'), nullable=False)
    coupon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('coupons.coupon_id'), nullable=True)
    price_at_selection: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payable_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"))

class PaymentMandate(Base):
    __tablename__ = 'payment_mandates'
    mandate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    cart_mandate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('cart_mandates.mandate_id'), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    authorization_type: Mapped[str] = mapped_column(String, nullable=False)
    authorized_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    razorpay_order_id: Mapped[str] = mapped_column(String, nullable=True)
    razorpay_payment_id: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="pending")
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False) # Guard against double charges
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"))

    __table_args__ = (
        CheckConstraint("authorization_type IN ('auto', 'user_confirmed')", name='check_auth_type'),
        CheckConstraint("status IN ('pending', 'captured', 'failed', 'refunded', 'pending_refund')", name='check_payment_status'),
    )

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=True)
    output_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=True)
    reasoning: Mapped[str] = mapped_column(String, nullable=True)
    prev_hash: Mapped[str] = mapped_column(String, nullable=True)
    curr_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"))

class PaymentToken(Base):
    __tablename__ = "payment_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    razorpay_customer_id: Mapped[str] = mapped_column(String, nullable=False)
    razorpay_token_id: Mapped[str] = mapped_column(String, nullable=False)
    card_last4: Mapped[str] = mapped_column(String, nullable=True)
    method_type: Mapped[str] = mapped_column(String, nullable=False) # 'card' or 'upi'
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"))
