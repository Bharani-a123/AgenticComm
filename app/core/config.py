from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, field_validator
from functools import lru_cache

class Settings(BaseSettings):
    # Core DBs
    database_url: str
    redis_url: str
    
    # Razorpay Secrets
    razorpay_key_id: str
    razorpay_key_secret: SecretStr
    razorpay_webhook_secret: SecretStr
    
    # Agent Secrets
    gemini_api_key: SecretStr
    llm_model: str = "gemini/gemini-2.5-flash"
    # anthropic_api_key: Optional[SecretStr] = None # removed as unused
    
    # Policies
    autopay_default_limit: float = 2500.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("razorpay_key_id")
    @classmethod
    def validate_rzp_key(cls, v: str) -> str:
        if not v.startswith("rzp_test_"):
            raise ValueError("RAZORPAY_KEY_ID must start with 'rzp_test_' (No live keys allowed in demo)")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must start with 'postgresql'")
        return v

@lru_cache()
def get_settings() -> Settings:
    return Settings()
