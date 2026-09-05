from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_chat import router as chat_router
from app.api.routes_audit import router as audit_router
from app.api.routes_webhooks import router as webhooks_router
from app.api.routes_checkout import router as checkout_router
from app.api.routes_payment_methods import router as payment_methods_router
from app.api.routes_onboarding import router as onboarding_router
from app.api.routes_orders import router as orders_router
from app.core.config import get_settings
from sqlalchemy import text

settings = get_settings()  # raises immediately if any required env var is missing/invalid

app = FastAPI(title="Agentic Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
app.include_router(checkout_router, prefix="/api")
app.include_router(payment_methods_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api/payment-methods")

@app.get("/health")
def health_check():
    from app.db.postgres import SessionLocal
    from app.db.redis import get_redis
    status = {"status": "ok", "postgres": "unknown", "redis": "unknown"}
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = f"error: {e}"
        status["status"] = "degraded"
    try:
        get_redis().ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {e}"
        status["status"] = "degraded"
    return status
from app.api.routes_wallet import router as wallet_router

app.include_router(orders_router, prefix="/api")
app.include_router(wallet_router, prefix="/api")
