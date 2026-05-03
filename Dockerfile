# ============================================
# Stage 1: Builder - Descargar modelo de embeddings
# ============================================
FROM python:3.11-slim AS builder

# Modelo de embeddings (configurable en build)
ARG EMBEDDING_MODEL="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

# Copiar solo lo necesario para descargar el modelo
COPY download_model.py .

# Descargar modelo de embeddings (fastembed usa ONNX, ~200MB)
ENV EMBEDDING_MODEL=${EMBEDDING_MODEL}
ARG HF_TOKEN
RUN HF_TOKEN=${HF_TOKEN} python download_model.py

# ============================================
# Stage 2: Runtime - Imagen final optimizada
# ============================================
FROM python:3.11-slim AS runtime

ARG EMBEDDING_MODEL="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

WORKDIR /app

# Copiar dependencias instaladas desde builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar modelo pre-descargado (fastembed cache)
COPY --from=builder /root/.cache/fastembed /root/.cache/fastembed

# Copiar código fuente
COPY swagger_utils.py .
COPY vector_store.py .
COPY init_swaggers.py .
COPY mcp_server.py .

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV EMBEDDING_MODEL=${EMBEDDING_MODEL}

# SWAGGER_URLS y SWAGGER_FILE se configuran al ejecutar el contenedor
# Ejemplo: docker run -e SWAGGER_URLS="url1,url2" swagger-rag-mcp

# El servidor MCP usa stdio
CMD ["python", "mcp_server.py"]
