import os

files = {
    'app/main.py': '''\\
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_chat import router as chat_router
from app.api.routes_audit import router as audit_router
from app.api.routes_webhooks import router as webhooks_router

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

@app.get("/health")
def health_check():
    return {"status": "ok"}
''',
    'app/agents/llm_client.py': '''\\
import os
import json
import logging
from litellm import completion

logger = logging.getLogger(__name__)

def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    \"\"\"
    Generic LLM client utilizing litellm. Supports ANY model.
    Defaults to Gemini (gemini/gemini-1.5-flash) but works with Claude, OpenAI, etc.
    \"\"\"
    model = os.getenv("LLM_MODEL", "gemini/gemini-1.5-flash")
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = completion(
            model=model,
            messages=messages,
            response_format={"type": "json_object"} if json_mode else None
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM Call Failed: {e}")
        raise
''',
    'app/api/routes_chat.py': '''\\
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.agents.state import ConversationState
from app.agents.graph import run_conversation_turn

router = APIRouter()

class ChatRequest(BaseModel):
    user_id: str
    message: Optional[str] = None
    state: Optional[Dict[str, Any]] = None

@router.post("/chat")
def chat_endpoint(req: ChatRequest):
    # Retrieve current state from frontend cache or initialize fresh
    current_state = req.state or ConversationState(
        user_id=req.user_id,
        raw_query="",
        category=None,
        constraints={},
        clarify_round=0,
        intent_mandate=None,
        candidate_products=[],
        selected_product_id=None,
        cart_mandate=None,
        messages=[],
        missing_fields=[],
        unsupported_category=False
    )
    
    try:
        new_state = run_conversation_turn(current_state, req.message)
        return {"state": new_state, "messages": new_state.get("messages", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
''',
    'app/api/routes_audit.py': '''\\
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.postgres import get_db
from app.db.models import AuditLog
from app.services.audit_ledger import verify_chain_integrity

router = APIRouter()

@router.get("/audit")
def get_audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.log_id.desc()).limit(50).all()
    is_valid, broken_id = verify_chain_integrity(db)
    
    return {
        "chain_valid": is_valid,
        "broken_log_id": broken_id,
        "logs": logs
    }
''',
    'app/mcp/razorpay_client.py': '''\\
import asyncio
import logging
import os
import json
from typing import Dict, Any
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

logger = logging.getLogger(__name__)

class RazorpayClientError(Exception):
    pass

async def _async_call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure MCP Server URL is configured, defaulting to our local docker service
    mcp_url = os.getenv("RAZORPAY_MCP_URL", "http://razorpay-mcp:3000/sse")
    try:
        async with sse_client(mcp_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return result.content[0].text if result.content else {}
    except Exception as e:
        logger.error(f"MCP Call Failed for {tool_name}: {e}")
        raise

def _call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Synchronous wrapper around the async MCP client for standard requests.\"\"\"
    try:
        res_text = asyncio.run(_async_call_mcp_tool(tool_name, arguments))
        if isinstance(res_text, str):
            try:
                return json.loads(res_text)
            except json.JSONDecodeError:
                return {"result": res_text}
        return res_text
    except Exception as e:
        raise RazorpayClientError(f"MCP Tool {tool_name} failed: {e}")

def create_order(amount: float, currency: str, receipt_id: str, notes: dict) -> dict:
    return _call_mcp_tool("create_order", {
        "amount": amount,
        "currency": currency,
        "receipt": receipt_id,
        "notes": notes
    })

def fetch_payment_status(razorpay_order_id: str) -> dict:
    return _call_mcp_tool("fetch_order", {"order_id": razorpay_order_id})

def capture_payment(payment_id: str, amount: float) -> dict:
    return _call_mcp_tool("capture_payment", {"payment_id": payment_id, "amount": amount})

def refund_payment(payment_id: str, amount: float, reason: str) -> dict:
    return _call_mcp_tool("refund_payment", {"payment_id": payment_id, "amount": amount, "notes": {"reason": reason}})
'''
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
