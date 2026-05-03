import os
from swagger_utils import load_swagger_from_file, fetch_swagger, parse_swagger
from vector_store import get_collection, get_collection_name, index_endpoints, search

# Configuración
SWAGGER_URL = "https://mdccal.xm.com.co/arcmdc/swagger/v1/swagger.json"
SWAGGER_FILE = "./swagger.json"

# 1. Cargar Swagger
if os.path.exists(SWAGGER_FILE):
    print(f"Cargando Swagger desde: {SWAGGER_FILE}")
    swagger_json = load_swagger_from_file(SWAGGER_FILE)
else:
    print(f"Descargando Swagger desde: {SWAGGER_URL}")
    swagger_json = fetch_swagger(SWAGGER_URL)

swagger_data = parse_swagger(swagger_json)
print(f"Encontrados {len(swagger_data)} endpoints")

# 2. Inicializar colección
collection_name = get_collection_name(SWAGGER_URL)
coleccion = get_collection(collection_name=collection_name)

# 3. Indexar si es necesario
if index_endpoints(coleccion, swagger_data):
    print("Endpoints vectorizados")
else:
    print(f"Colección cargada con {coleccion.count()} documentos")

# 4. Buscar
query = "Obtener atributos segun su ID"
print(f"\nBuscando: '{query}'")

resultado = search(coleccion, query)
print("\n--- RESULTADO ---")
print(resultado[0] if resultado else "No encontrado")