from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEFAULT_MODEL: str = "gemini-1.5-flash"
    GOOGLE_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    GLM_API_KEY: str | None = None
    KIMI_API_KEY: str | None = None

    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"

    API_KEY: str = "change-me-in-production"
    DATABASE_URL: str = "sqlite:///./genai_jobs.db"

    PORT: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()
