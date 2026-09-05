import os

env_content = '''\\
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=agentic_commerce
DATABASE_URL=postgresql://admin:admin@postgres:5432/agentic_commerce
REDIS_URL=redis://redis:6379/0

GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=dummy_anthropic_key_because_we_are_using_gemini

RAZORPAY_KEY_ID=rzp_test_your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
RAZORPAY_MCP_URL=http://razorpay-mcp:3000/sse
'''

with open(".env", "w") as f:
    f.write(env_content)

llm_client = '''\\
import os
import json
import logging
import requests
from litellm import completion

logger = logging.getLogger(__name__)

_CACHED_MODEL = None

def discover_best_gemini_model(api_key: str) -> str:
    """Queries the Gemini API to find the most capable available model."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        resp = requests.get(url)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            
            # Filter for active gemini models that support text generation
            gemini_models = [
                m["name"].replace("models/", "") 
                for m in models 
                if "models/gemini" in m["name"] and "generateContent" in m.get("supportedGenerationMethods", [])
            ]
            
            logger.info(f"Discovered Gemini models: {gemini_models}")
            
            # Prioritize newer models available in 2026, fallback gracefully
            for preferred in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-pro"]:
                if preferred in gemini_models:
                    return f"gemini/{preferred}"
                    
            if gemini_models:
                return f"gemini/{gemini_models[-1]}" # Pick the last one in the list if no preferred found
    except Exception as e:
        logger.error(f"Failed to discover models dynamically: {e}")
    
    # Absolute fallback if network fails
    return "gemini/gemini-2.0-flash"

def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    Generic LLM client utilizing litellm.
    Automatically discovers and uses the best available Gemini model based on the API key.
    """
    global _CACHED_MODEL
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not _CACHED_MODEL and api_key and api_key != "your_gemini_api_key_here":
        _CACHED_MODEL = discover_best_gemini_model(api_key)
        logger.info(f"Auto-selected Gemini model: {_CACHED_MODEL}")
        
    model = _CACHED_MODEL or "gemini/gemini-2.0-flash"
    
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
        logger.error(f"LLM Call Failed using model {model}: {e}")
        raise
'''

with open("app/agents/llm_client.py", "w") as f:
    f.write(llm_client)
