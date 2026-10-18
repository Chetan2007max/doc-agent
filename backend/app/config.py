from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./docagent.db"
    llm_provider: str = "auto"          # auto | gemini | heuristic
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    tolerance_pct: float = 1.0          # tolerance-based exception flagging
    max_llm_retries: int = 2
    upload_dir: str = "./uploads"
    max_upload_mb: int = 10
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
