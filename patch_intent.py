with open('app/agents/agent_intent.py', 'r') as f:
    content = f.read()

replacement = '''
    constraints_raw = resp.get("constraints", {})
    if isinstance(constraints_raw, list):
        constraints_raw = {}
        
    for k, v in constraints_raw.items():
'''

content = content.replace(
    'for k, v in resp.get("constraints", {}).items():',
    replacement
)

with open('app/agents/agent_intent.py', 'w') as f:
    f.write(content)
