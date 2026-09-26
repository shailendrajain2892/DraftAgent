# DraftAgent image: builds the React UI, then serves it from the FastAPI backend
# (same origin -> the session cookie just works, no CORS). Build context is the repo root.

# --- Stage 1: build the web UI (mocks off -> talks to the real backend) ---
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
ENV VITE_USE_MOCKS=false
RUN npm run build            # -> /web/dist

# --- Stage 2: backend + the built UI ---
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for layer caching. README is needed by the hatchling build.
COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
RUN pip install --upgrade pip && pip install -e ".[agent]"

# Serve the built UI from FastAPI (main.py reads WEB_DIST).
COPY --from=web /web/dist ./web_dist
ENV WEB_DIST=/app/web_dist

EXPOSE 8080

# One worker on purpose: sessions/tokens live in process memory.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
