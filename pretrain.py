"""
Script de pre-entrenamiento para Docker.
Se ejecuta durante el build para:
1. Descargar el modelo de embeddings
2. Vectorizar los Swaggers desde múltiples URLs
"""
import json
import os

# Importar módulos
from vector_store import get_collection, index_endpoints, embedding_fn, EMBEDDING_MODEL
from swagger_utils import load_swagger_from_file, fetch_swagger, parse_swagger

# URLs separadas por coma, o archivo local
SWAGGER_URLS = os.environ.get("SWAGGER_URLS", "")
SWAGGER_FILE = os.environ.get("SWAGGER_FILE", "")
COLLECTION_NAME = "swagger_rag"

def pretrain():
    print("=== PRE-ENTRENAMIENTO ===")
    
    # 1. Mostrar modelo de embeddings
    print(f"1. Modelo de embeddings: {EMBEDDING_MODEL}")
    
    all_endpoints = []
    
    # 2. Cargar desde URLs
    if SWAGGER_URLS:
        urls = [url.strip() for url in SWAGGER_URLS.split(",") if url.strip()]
        print(f"2. Cargando {len(urls)} Swagger(s) desde URLs...")
        
        for url in urls:
            try:
                print(f"   - Descargando: {url}")
                swagger_json = fetch_swagger(url)
                endpoints = parse_swagger(swagger_json)
                # Agregar metadata de origen
                for ep in endpoints:
                    ep["source_url"] = url
                all_endpoints.extend(endpoints)
                print(f"     Encontrados: {len(endpoints)} endpoints")
            except Exception as e:
                print(f"     ERROR: {e}")
    
    # 3. Cargar desde archivo local si existe
    if SWAGGER_FILE and os.path.exists(SWAGGER_FILE):
        print(f"3. Cargando Swagger desde archivo: {SWAGGER_FILE}")
        swagger_json = load_swagger_from_file(SWAGGER_FILE)
        endpoints = parse_swagger(swagger_json)
        for ep in endpoints:
            ep["source_url"] = SWAGGER_FILE
        all_endpoints.extend(endpoints)
        print(f"   Encontrados: {len(endpoints)} endpoints")
    
    if not all_endpoints:
        print("ERROR: No se encontraron endpoints para indexar")
        return
    
    print(f"\nTotal endpoints a indexar: {len(all_endpoints)}")
    
    # 4. Crear colección y vectorizar
    print("4. Vectorizando endpoints...")
    coleccion = get_collection(collection_name=COLLECTION_NAME)
    
    if index_endpoints(coleccion, all_endpoints):
        print("   Vectorización completada")
    else:
        print(f"   Colección ya existía con {coleccion.count()} documentos")
    
    # 5. Verificar
    print(f"5. Verificación: {coleccion.count()} documentos indexados")
    
    print("=== PRE-ENTRENAMIENTO COMPLETO ===")

if __name__ == "__main__":
    pretrain()
