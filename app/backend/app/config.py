from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    database_sync_url: str
    secret_key: str
    openai_api_key: str
    upload_dir: str = "/uploads"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours

    class Config:
        env_file = ".env"


settings = Settings()
