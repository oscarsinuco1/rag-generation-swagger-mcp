"""
Script para descargar el modelo de embeddings durante el build.
Solo descarga el modelo, no vectoriza datos.
"""
import os
import sys

# Importar para forzar descarga del modelo
from vector_store import embedding_fn, EMBEDDING_MODEL

print(f"Modelo descargado: {EMBEDDING_MODEL}", file=sys.stderr)
print("Listo para usar en runtime", file=sys.stderr)
