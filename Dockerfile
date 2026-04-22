FROM python:3.11-slim

WORKDIR /app

# Install system deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    && playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers
RUN playwright install chromium

COPY pyproject.toml .
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
