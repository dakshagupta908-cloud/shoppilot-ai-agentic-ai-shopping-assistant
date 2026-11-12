from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./shoppilot.db"
    frontend_url: str = "http://localhost:5173"
    ai_provider: str = ""
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"
    paypal_inr_to_usd_rate: float = 0.012

    @field_validator("paypal_base_url")
    @classmethod
    def require_paypal_sandbox(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if normalized != "https://api-m.sandbox.paypal.com":
            raise ValueError("Only the PayPal Sandbox API host is allowed.")
        return normalized

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
