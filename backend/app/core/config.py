from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SenAI Agentic CRM"
    database_url: str = Field("sqlite:///./senai.db", alias="DATABASE_URL")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-5.5", alias="OPENAI_MODEL")
    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")
    chroma_host: str = Field("chroma", alias="CHROMA_HOST")
    chroma_port: int = Field(8000, alias="CHROMA_PORT")
    offline_mode: bool = Field(True, alias="OFFLINE_MODE")

    class Config:
        env_file = ".env"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
