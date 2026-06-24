from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Deepseek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    DEEPSEEK_ENDPOINT: str = "https://api.deepseek.com"

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "ai-agent-index"
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"

    # Tavily
    TAVILY_API_KEY: str = ""

    # LangSmith — supports both old (LANGCHAIN_*) and new (LANGSMITH_*) naming
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = ""
    LANGCHAIN_ENDPOINT: str = ""
    LANGSMITH_TRACING: str = ""  # "true" / "false" (new SDK naming)
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = ""
    LANGSMITH_ENDPOINT: str = ""

    # Postgres (optional — falls back to InMemorySaver when empty)
    DATABASE_URL: str = ""

    # App
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
