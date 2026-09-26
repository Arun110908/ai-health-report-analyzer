# Build the React dashboard.
FROM node:20-bookworm-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Run the FastAPI service and serve the compiled dashboard from the same origin.
FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    STATIC_DIR=/app/static

# Tesseract and Poppler enable OCR and scanned-PDF support.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
# The deployed demo is functional immediately. This uses only generated,
# clearly labelled synthetic data; no patient reports are embedded in the image.
ARG TRAIN_DEMO_RISK_MODEL=true
# The training step must NEVER fail the whole image build (a Render
# free-tier build machine can be slow/memory-limited): if it errors out for
# any reason, the app still deploys and simply reports the risk feature as
# "model_not_trained" instead of crash-looping the entire deployment.
RUN if [ "$TRAIN_DEMO_RISK_MODEL" = "true" ]; then \
      cd /app/backend \
      && (python scripts/generate_demo_risk_data.py --rows 600 \
          && python scripts/train_risk_model.py --input data/demo_metabolic_risk.csv \
          || echo "WARNING: risk-model training failed or was skipped; the app will still deploy and run in rule-based mode."); \
    fi
COPY --from=frontend-build /frontend/dist /app/static

WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
