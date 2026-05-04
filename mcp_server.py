import sys
import os

# Solo agregar path de Windows si existe (desarrollo local)
if os.path.exists(r"C:\st"):
    sys.path.insert(0, r"C:\st")

import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from vector_store import get_collection, search
from init_swaggers import init_swaggers

# Inicializar servidor MCP
server = Server("swagger-rag")

# Cargar colección al inicio
COLLECTION_NAME = "swagger_rag"
coleccion = None

def initialize():
    """Inicializa los Swaggers si hay configuración."""
    global coleccion
    swagger_urls = os.environ.get("SWAGGER_URLS", "")
    swagger_file = os.environ.get("SWAGGER_FILE", "")
    swagger_urls_file = os.environ.get("SWAGGER_URLS_FILE", "/app/urls.txt")
    force_refresh = os.environ.get("FORCE_REFRESH", "false").lower() == "true"
    
    # Verificar si hay archivo de URLs o variables de entorno
    has_urls_file = os.path.exists(swagger_urls_file)
    
    if swagger_urls or swagger_file or has_urls_file or force_refresh:
        # Hay configuración o se fuerza refresh, vectorizar
        coleccion = init_swaggers()
    else:
        # Usar colección existente
        coleccion = get_collection(collection_name=COLLECTION_NAME)


@server.list_tools()
async def list_tools():
    """Lista las herramientas disponibles."""
    return [
        Tool(
            name="search_endpoint",
            description="Busca un endpoint en el Swagger por descripción semántica. Útil para encontrar APIs relacionadas con una funcionalidad.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Descripción de lo que busca el usuario, ej: 'obtener usuario por ID'"
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Número de resultados a retornar (default: 3)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_all_endpoints",
            description="Lista todos los endpoints disponibles en el Swagger.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Ejecuta una herramienta."""
    global coleccion
    
    if coleccion is None:
        coleccion = get_collection(collection_name=COLLECTION_NAME)
    
    if name == "search_endpoint":
        query = arguments.get("query", "")
        n_results = arguments.get("n_results", 3)
        
        resultados = search(coleccion, query, n_results=n_results)
        
        if not resultados:
            return [TextContent(type="text", text="No se encontraron endpoints.")]
        
        # Formatear resultados
        formatted = []
        for i, doc in enumerate(resultados, 1):
            endpoint = json.loads(doc)
            source = endpoint.get("source_url", "unknown")
            
            result_text = (
                f"{i}. {endpoint['method']} {endpoint['path']}\n"
                f"   Summary: {endpoint['summary']}\n"
                f"   Description: {endpoint.get('description', 'N/A')}\n"
                f"   Parameters: {', '.join(endpoint['parameters']) or 'none'}"
            )
            
            # Agregar requestBody si existe
            request_body = endpoint.get("requestBody")
            if request_body:
                result_text += f"\n   Content-Type: {request_body.get('content_type', 'N/A')}"
                if request_body.get("example"):
                    example_json = json.dumps(request_body["example"], indent=2, ensure_ascii=False)
                    result_text += f"\n   Request Body Example:\n{example_json}"
            
            result_text += f"\n   Source: {source}"
            formatted.append(result_text)
        
        return [TextContent(type="text", text="\n\n".join(formatted))]
    
    elif name == "list_all_endpoints":
        # Obtener todos los documentos
        all_docs = coleccion.get()
        
        if not all_docs['documents']:
            return [TextContent(type="text", text="No hay endpoints indexados.")]
        
        # Agrupar por source
        by_source = {}
        for doc in all_docs['documents']:
            endpoint = json.loads(doc)
            source = endpoint.get("source_url", "unknown")
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(f"  - {endpoint['method']} {endpoint['path']}: {endpoint['summary']}")
        
        formatted = []
        for source, endpoints in by_source.items():
            formatted.append(f"📄 {source}\n" + "\n".join(endpoints))
        
        return [TextContent(type="text", text="\n\n".join(formatted))]
    
    return [TextContent(type="text", text=f"Herramienta '{name}' no encontrada.")]


async def main():
    """Inicia el servidor MCP."""
    # Inicializar Swaggers antes de aceptar conexiones
    initialize()
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
