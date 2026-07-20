# ─── Build Stage ────────────────────────────────────────────
ARG BASE_IMAGE=python:3.12-slim
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ─── Runtime Stage ─────────────────────────────────────────
# Default is a slim CPU image (BASE_IMAGE ARG set above). Pass --build-arg BASE_IMAGE=nvidia/cuda:... for GPU support.
FROM ${BASE_IMAGE} AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgl1-mesa-glx libglib2.0-0 tesseract-ocr && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r veriunlearn && useradd -r -g veriunlearn -d /app -s /sbin/nologin veriunlearn

COPY --from=builder /root/.local /root/.local
COPY --chown=veriunlearn:veriunlearn . .

ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER veriunlearn

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
