FROM python:3.11-slim

WORKDIR /app

# Install UV
RUN pip install uv

COPY pyproject.toml .
RUN uv sync --no-dev
RUN uv run python -m spacy download en_core_web_lg

COPY app/ ./app/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
