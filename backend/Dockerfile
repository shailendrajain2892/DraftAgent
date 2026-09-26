# DraftAgent backend image. Single-process (in-memory sessions require one worker).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for layer caching. README is needed by the hatchling build.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --upgrade pip && pip install -e ".[agent]"

# Fly routes to internal_port 8080 (see fly.toml).
EXPOSE 8080

# One worker on purpose: sessions/tokens live in process memory.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
