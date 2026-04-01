# ─────────────────────────────────────────────────────────────────────
# CaVMorph-AI — Web Deployment
# Two-stage build: Node (frontend) → Python (inference + API)
# ─────────────────────────────────────────────────────────────────────

# ── Stage 1: Build the Vue SPA ──────────────────────────────────────
FROM node:20-slim AS frontend

WORKDIR /app/desktop
COPY desktop/package.json desktop/package-lock.json* ./

RUN npm ci --ignore-scripts 2>/dev/null || npm install --ignore-scripts

COPY desktop/ ./
RUN npm run build:web

# ── Stage 2: Python inference runtime ────────────────────────────────
FROM python:3.11-slim

# System deps for OpenCV
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY inference_runtime/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt python-multipart

# Copy inference runtime
COPY inference_runtime/ /app/inference_runtime/

# Model files are bind-mounted at runtime via docker-compose (not baked into image).
# Create the directory so the container starts even before the mount is attached.
RUN mkdir -p /app/models/cavfish_v1

# Copy built frontend from stage 1
COPY --from=frontend /app/desktop/dist-web /app/static

# Copy supporting code that may be imported
COPY custom_transforms.py /app/custom_transforms.py
COPY phenolosses/ /app/phenolosses/

# Environment
ENV FISH_MODEL_DIR=/app/models/cavfish_v1 \
    CAVMORPH_AI_STATIC_DIR=/app/static \
    CAVMORPH_AI_HOST=0.0.0.0 \
    CAVMORPH_AI_PORT=8008 \
    CAVMORPH_AI_UPLOAD_DIR=/app/uploads

# Create upload directory
RUN mkdir -p /app/uploads

EXPOSE 8008

CMD ["python", "-m", "inference_runtime.runtime_server"]
