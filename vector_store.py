import sys
import os

# Solo agregar path de Windows si existe (desarrollo local)
if os.path.exists(r"C:\st"):
    sys.path.insert(0, r"C:\st")

# Forzar ubicación del cache de fastembed
os.environ.setdefault("FASTEMBED_CACHE_PATH", "/root/.cache/fastembed")

import json
import hashlib
import chromadb
from fastembed import TextEmbedding

# Modelo configurable via variable de entorno
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL", 
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# Inicializar modelo fastembed (ONNX, mucho más ligero)
_embedding_model = None

def get_embedding_model():
    """Lazy loading del modelo de embeddings."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL)
    return _embedding_model


class FastEmbedFunction:
    """Wrapper de fastembed para ChromaDB."""
    
    def name(self):
        """Nombre de la función de embeddings (requerido por ChromaDB)."""
        return "fastembed"
    
    def __call__(self, input):
        model = get_embedding_model()
        embeddings = list(model.embed(input))
        return embeddings
    
    def embed_query(self, input):
        """Genera embedding para una query (requerido por ChromaDB para búsquedas)."""
        model = get_embedding_model()
        # input puede ser string o lista
        if isinstance(input, str):
            embeddings = list(model.embed([input]))
            return embeddings[0]
        else:
            embeddings = list(model.embed(input))
            return embeddings

embedding_fn = FastEmbedFunction()


def get_collection_name(identifier):
    """Genera un nombre único para la colección basado en un identificador."""
    url_hash = hashlib.md5(identifier.encode()).hexdigest()[:8]
    return f"swagger_{url_hash}_multilingual"


def get_collection(db_path="./chroma_db", collection_name="swagger"):
    """Obtiene o crea una colección de ChromaDB."""
    chroma_client = chromadb.PersistentClient(path=db_path)
    return chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn
    )


def create_searchable_text(endpoint):
    """Crea un texto optimizado para búsqueda semántica."""
    parts = []
    
    # Método y path son importantes
    parts.append(f"{endpoint.get('method', '')} {endpoint.get('path', '')}")
    
    # Summary y description son los más importantes para búsqueda
    if endpoint.get('summary'):
        parts.append(endpoint['summary'])
    if endpoint.get('description'):
        parts.append(endpoint['description'])
    
    # Tags ayudan a categorizar
    if endpoint.get('tags'):
        parts.append(f"Tags: {', '.join(endpoint['tags'])}")
    
    # Nombres de parámetros pueden ser relevantes
    params = endpoint.get('parameters', [])
    if params:
        param_names = [p.get('name', '') for p in params if isinstance(p, dict)]
        if param_names:
            parts.append(f"Parameters: {', '.join(param_names)}")
    
    # Schema del request body
    request_body = endpoint.get('requestBody')
    if request_body:
        schema = request_body.get('schema') or {}
        if schema.get('schema_name'):
            parts.append(f"Request body: {schema['schema_name']}")
        if schema.get('properties'):
            props = list(schema['properties'].keys())
            parts.append(f"Body fields: {', '.join(props)}")
    
    # Schema de response principal (200)
    responses = endpoint.get('responses') or {}
    if '200' in responses and responses['200']:
        resp_schema = responses['200'].get('schema') or {}
        if resp_schema.get('schema_name'):
            parts.append(f"Returns: {resp_schema['schema_name']}")
    
    return " | ".join(parts)


def index_endpoints(coleccion, swagger_data):
    """Indexa los endpoints en la colección."""
    # Crear textos optimizados para búsqueda
    searchable_texts = [create_searchable_text(ep) for ep in swagger_data]
    
    # Guardar JSON completo como metadatos
    documentos = [json.dumps(endpoint, ensure_ascii=False) for endpoint in swagger_data]
    ids = [f"endpoint_{i}" for i in range(len(swagger_data))]
    
    # Usar el texto semántico para embeddings, JSON como documento
    coleccion.add(
        documents=searchable_texts,
        metadatas=[{"full_json": doc} for doc in documentos],
        ids=ids
    )
    return True


def search(coleccion, query, n_results=1):
    """Busca en la colección por similitud semántica."""
    resultados = coleccion.query(
        query_texts=[query],
        n_results=n_results,
        include=["metadatas", "documents"]
    )
    
    # Devolver el JSON completo desde metadatas
    if resultados['metadatas'] and resultados['metadatas'][0]:
        return [m.get('full_json', '{}') for m in resultados['metadatas'][0]]
    return []
