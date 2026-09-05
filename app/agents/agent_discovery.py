from app.agents.state import ConversationState
from app.db.postgres import SessionLocal
from app.db.models import Product
from app.services.ranking_pre_filter import pre_filter_products
from app.protocols.acp.adapter import discover_products, attach_effective_pricing
from app.services.audit_ledger import write_audit_log

def run_discovery_agent(state: ConversationState) -> ConversationState:
    if not state.get("intent_mandate"):
        return state
        
    try:
        category = state["intent_mandate"].category
        # 1. Genuine parallel ACP fetch
        raw_list = discover_products(category)
        
        # 2. Attach coupon-aware pricing
        raw_list = attach_effective_pricing(raw_list)
            
        # 3. Pre-filter BEFORE LLM
        filtered = pre_filter_products(raw_list, state["intent_mandate"])
        
        db_audit = SessionLocal()
        try:
            write_audit_log(
                db_audit, "discovery_agent", "products_filtered",
                state["intent_mandate"].mandate_id,
                {"total_found": len(raw_list)},
                {"eligible_after_filter": len(filtered)},
                f"Filtered {len(raw_list) - len(filtered)} products (over-budget/out-of-stock/wrong-category)."
            )
        finally:
            db_audit.close()
            
        if not filtered:
            state["candidate_products"] = []
            if "messages" not in state: state["messages"] = []
            state["messages"].append({"role": "assistant", "content": "No matches found."})
        else:
            state["candidate_products"] = filtered
            if "messages" not in state: state["messages"] = []
            state["messages"].append({"role": "assistant", "content": f"I found {len(filtered)} products matching your criteria. Here are the top picks:"})
            
    except Exception as e:
        import logging, traceback
        logging.getLogger(__name__).error(f"Discovery error: {e}\n{traceback.format_exc()}")
        state["candidate_products"] = []
        if "messages" not in state: state["messages"] = []
        state["messages"].append({"role": "assistant", "content": f"Something went wrong while searching for products: {e}"})

    return state
