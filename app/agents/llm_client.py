import os
import logging
import time
from litellm import completion

logger = logging.getLogger(__name__)

from app.core.config import get_settings

def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    Generic LLM client utilizing litellm with fallback models and retry logic for Rate Limits.
    """
    settings = get_settings()
    base_model = settings.llm_model
    
    fallback_models = [
        base_model,
        "groq/qwen/qwen3.8-27b",
        "groq/groq/compound"
    ]
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    max_retries = 3
    
    for attempt in range(max_retries):
        last_exception = None
        for model_to_use in fallback_models:
            try:
                response = completion(
                    model=model_to_use,
                    messages=messages,
                    response_format={"type": "json_object"} if json_mode else None
                )
                return response.choices[0].message.content
            except Exception as e:
                last_exception = e
                err_str = str(e).lower()
                
                # If we hit a Rate Limit or Quota issue, STOP trying fallback models immediately.
                # Fallback models share the same API key quota, so trying them just gets us blocked longer.
                if "429" in err_str or "ratelimit" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                    logger.warning(f"Rate limited on {model_to_use}. Sleeping for 20 seconds before retry (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(20)
                    break # Break out of the inner fallback loop to trigger the outer retry loop
                else:
                    logger.warning(f"LLM Call Failed using model {model_to_use}: {e}. Trying next fallback model...")
                    
        # If the outer loop finishes a retry cycle and the exception wasn't a rate limit, it means all models failed for other reasons.
        if last_exception and not any(kw in str(last_exception).lower() for kw in ["429", "ratelimit", "resource_exhausted", "quota"]):
            break
            
    logger.error("All retries exhausted or catastrophic failure.")
    raise last_exception
