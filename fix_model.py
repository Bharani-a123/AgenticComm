import os

# Update .env
with open('.env', 'r') as f:
    env_content = f.read()

env_content = env_content.replace('gemini/gemini-2.5-flash', 'gemini/gemini-3.6-flash')

with open('.env', 'w') as f:
    f.write(env_content)

# Update llm_client.py
with open('app/agents/llm_client.py', 'r') as f:
    client_content = f.read()
    
client_content = client_content.replace('gemini/gemini-2.5-flash', 'gemini/gemini-3.6-flash')

with open('app/agents/llm_client.py', 'w') as f:
    f.write(client_content)
