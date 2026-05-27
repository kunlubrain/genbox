from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DEFAULT_MODEL: str = "gemini-1.5-flash"
    
    # Internal LLM API Keys (Ours, stored in .env)
    GOOGLE_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    GLM_API_KEY: str | None = None
    KIMI_API_KEY: str | None = None

    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"

    # Authorized Tokens for accessing this API
    # Should be a comma-separated string in .env: "token1,token2,token3"
    AUTHORIZED_TOKENS_STR: str = "change-me-in-production"
    
    # We will convert the string to a set for O(1) lookup
    AUTHORIZED_TOKENS: set[str] = set()

    @field_validator("AUTHORIZED_TOKENS", mode="before")
    @classmethod
    def parse_tokens(cls, v, info):
        # This handles the internal population after the string is loaded
        tokens_str = info.data.get("AUTHORIZED_TOKENS_STR", "")
        return {t.strip() for t in tokens_str.split(",") if t.strip()}

    DATABASE_URL: str = "sqlite:///./genai_jobs.db"
    PORT: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
# Ensure the set is populated if the validator didn't run as expected in some pydantic versions
if not settings.AUTHORIZED_TOKENS:
    settings.AUTHORIZED_TOKENS = {t.strip() for t in settings.AUTHORIZED_TOKENS_STR.split(",") if t.strip()}
