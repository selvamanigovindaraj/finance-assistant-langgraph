from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_GENERATION_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_ROUTING_MODEL: str = "claude-haiku-4-5-20251001"

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "ai-agent-index"
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"

    # Tavily
    TAVILY_API_KEY: str = ""

    # LangSmith
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "ai-agent"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # App
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
