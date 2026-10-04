# ---- build frontend ----
FROM node:20-slim AS fe
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- runtime ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
# CPU-only torch first (CUDA wheels are GBs); requirements' torch>=2.2 then resolves as satisfied.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=fe /build/dist ./frontend-dist
ENV FRONTEND_DIST=/app/frontend-dist
EXPOSE 8000
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
