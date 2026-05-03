"""
Script de inicio para Docker.
Se ejecuta al iniciar el contenedor para vectorizar Swaggers.
"""
import json
import os
import sys

from vector_store import get_collection, index_endpoints, EMBEDDING_MODEL
from swagger_utils import load_swagger_from_file, fetch_swagger, parse_swagger

# Configuración desde variables de entorno
SWAGGER_URLS = os.environ.get("SWAGGER_URLS", "")
SWAGGER_FILE = os.environ.get("SWAGGER_FILE", "")
SWAGGER_URLS_FILE = os.environ.get("SWAGGER_URLS_FILE", "/app/urls.txt")
COLLECTION_NAME = "swagger_rag"

def load_urls_from_file(filepath: str) -> list[str]:
    """Carga URLs desde un archivo de texto, una por línea."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def init_swaggers():
    """Inicializa los Swaggers al arrancar el contenedor."""
    print("=== INICIALIZANDO SWAGGERS ===", file=sys.stderr)
    print(f"Modelo: {EMBEDDING_MODEL}", file=sys.stderr)
    
    all_endpoints = []
    urls = []
    
    # Prioridad: archivo > variable de entorno
    if os.path.exists(SWAGGER_URLS_FILE):
        urls = load_urls_from_file(SWAGGER_URLS_FILE)
        print(f"Cargando {len(urls)} URL(s) desde archivo: {SWAGGER_URLS_FILE}", file=sys.stderr)
    elif SWAGGER_URLS:
        urls = [url.strip() for url in SWAGGER_URLS.split(",") if url.strip()]
        print(f"Cargando {len(urls)} URL(s) desde variable de entorno", file=sys.stderr)
    
    # Cargar desde URLs
    for url in urls:
        try:
            print(f"  - {url}", file=sys.stderr)
            swagger_json = fetch_swagger(url)
            endpoints = parse_swagger(swagger_json)
            for ep in endpoints:
                ep["source_url"] = url
            all_endpoints.extend(endpoints)
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
    
    # Cargar desde archivo local
    if SWAGGER_FILE and os.path.exists(SWAGGER_FILE):
        print(f"Cargando desde archivo: {SWAGGER_FILE}", file=sys.stderr)
        swagger_json = load_swagger_from_file(SWAGGER_FILE)
        endpoints = parse_swagger(swagger_json)
        for ep in endpoints:
            ep["source_url"] = SWAGGER_FILE
        all_endpoints.extend(endpoints)
    
    if not all_endpoints:
        print("ADVERTENCIA: No hay endpoints para indexar", file=sys.stderr)
        return None
    
    print(f"Total: {len(all_endpoints)} endpoints", file=sys.stderr)
    
    # Vectorizar
    coleccion = get_collection(collection_name=COLLECTION_NAME)
    
    # Limpiar colección existente si hay nuevos datos
    if coleccion.count() > 0:
        print("Limpiando colección existente...", file=sys.stderr)
        # Eliminar todos los documentos
        all_ids = coleccion.get()['ids']
        if all_ids:
            coleccion.delete(ids=all_ids)
    
    index_endpoints(coleccion, all_endpoints)
    print(f"Indexados: {coleccion.count()} documentos", file=sys.stderr)
    print("=== LISTO ===", file=sys.stderr)
    
    return coleccion

if __name__ == "__main__":
    init_swaggers()
