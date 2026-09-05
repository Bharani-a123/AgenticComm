from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.postgres import get_db
from app.db.models import PaymentToken
from app.mcp.razorpay_client import create_customer, _call_mcp_tool
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class RegisterRequest(BaseModel):
    user_id: str = "demo_user"
    email: str = "demo@test.com"
    contact: str = "9999999999"
    name: str = "Demo User"

@router.post("/register")
def register_token_endpoint(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Step 2: One-time token registration.
    """
    try:
        # 1. Create Customer
        customer = create_customer(req.name, req.email, req.contact)
        customer_id = customer.get("id")

        import requests, os
        key_id = os.getenv('RAZORPAY_KEY_ID')
        key_secret = os.getenv('RAZORPAY_KEY_SECRET')
        
        # 2. Create an explicit MANDATE order so Razorpay vaults the token
        res = requests.post('https://api.razorpay.com/v1/orders', auth=(key_id, key_secret), json={
            'amount': 100, 
            'currency': 'INR', 
            'method': 'card', 
            'customer_id': customer_id, 
            'receipt': f"reg_{req.user_id}",
            'notes': {"user_id": req.user_id, "registration": "true"},
            'token': { 'max_amount': 20000000, 'expire_at': 2000000000, 'frequency': 'as_presented' }
        })
        order_resp = res.json()
        order_id = order_resp.get("id")

        if not order_id:
            raise ValueError(f"Failed to create registration order: {order_resp}")

        # 3. Return order_id + customer_id to frontend
        return {
            "order_id": order_id,
            "customer_id": customer_id,
            "amount": 100,
            "currency": "INR",
            "message": "Please complete the Razorpay checkout to register your token."
        }
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(500, str(e))
