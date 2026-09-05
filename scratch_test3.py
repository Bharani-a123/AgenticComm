from app.agents.state import ConversationState
from app.agents.graph import run_conversation_turn
state = ConversationState(raw_query='', constraints={}, messages=[], clarify_round=0)
final_state = run_conversation_turn(state, 'material: cotton, budget_max: 500, color: green, occasion: casual')
print('Extracted category:', final_state.get('intent_mandate').category if final_state.get('intent_mandate') else 'None')
print('Messages:', [m.get('content') for m in final_state.get('messages', [])])
