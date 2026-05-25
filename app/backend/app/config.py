from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    database_sync_url: str
    secret_key: str
    openai_api_key: str
    upload_dir: str = "/uploads"
    register_secret: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480


settings = Settings()
