FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiamos primero los manifests (sin el -r relativo de backend/requirements.txt
# que no funciona aqui porque la ruta relativa se resuelve respecto a /tmp).
COPY requirements.txt /tmp/root-requirements.txt
COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/root-requirements.txt && \
    grep -v '^-r ' /tmp/backend-requirements.txt > /tmp/backend-only.txt && \
    pip install -r /tmp/backend-only.txt

# El backend reusa modulos del proyecto raiz, asi que copiamos todo el arbol
COPY . /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

WORKDIR /app/backend
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
