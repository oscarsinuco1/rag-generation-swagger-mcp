"""
Script para descargar el modelo de embeddings durante el build.
Solo descarga el modelo, no vectoriza datos.
"""
import os
import sys

# Forzar ubicación del cache
os.environ["FASTEMBED_CACHE_PATH"] = "/root/.cache/fastembed"

# Token de Hugging Face para descargas autenticadas
HF_TOKEN = os.environ.get("HF_TOKEN", "")
if HF_TOKEN:
    os.environ["HF_TOKEN"] = HF_TOKEN
    print(f"Usando HF_TOKEN para autenticación", file=sys.stderr)

from fastembed import TextEmbedding

EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

print(f"Descargando modelo: {EMBEDDING_MODEL}", file=sys.stderr)
model = TextEmbedding(model_name=EMBEDDING_MODEL)
# Forzar descarga haciendo un embedding de prueba
list(model.embed(["test"]))
print(f"Modelo descargado: {EMBEDDING_MODEL}", file=sys.stderr)
print("Listo para usar en runtime", file=sys.stderr)
