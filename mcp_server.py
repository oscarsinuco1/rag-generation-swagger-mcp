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


def _indent(text, spaces):
    """Indenta un texto multilínea."""
    indent = " " * spaces
    return "\n".join(indent + line for line in text.split("\n"))


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
            )
            
            # Formatear parámetros con detalles
            params = endpoint.get('parameters', [])
            if params:
                if isinstance(params[0], dict):
                    # Nuevo formato con detalles
                    param_lines = []
                    for p in params:
                        req = "*" if p.get("required") else ""
                        param_line = f"      - {p['name']}{req} ({p.get('in', 'query')}): {p.get('type', 'string')}"
                        if p.get("description"):
                            param_line += f" - {p['description']}"
                        if p.get("enum"):
                            param_line += f" [enum: {', '.join(str(e) for e in p['enum'])}]"
                        param_lines.append(param_line)
                    result_text += f"   Parameters:\n" + "\n".join(param_lines) + "\n"
                else:
                    # Formato antiguo (solo nombres)
                    result_text += f"   Parameters: {', '.join(params)}\n"
            else:
                result_text += "   Parameters: none\n"
            
            # Agregar requestBody si existe
            request_body = endpoint.get("requestBody")
            if request_body:
                result_text += f"   Request Body:\n"
                result_text += f"      Content-Type: {request_body.get('content_type', 'N/A')}\n"
                result_text += f"      Required: {request_body.get('required', False)}\n"
                
                schema = request_body.get("schema")
                if schema:
                    if schema.get("schema_name"):
                        result_text += f"      Schema: {schema['schema_name']}\n"
                    if schema.get("required"):
                        result_text += f"      Required fields: {', '.join(schema['required'])}\n"
                    if schema.get("properties"):
                        result_text += f"      Properties:\n"
                        for prop_name, prop_info in schema["properties"].items():
                            prop_type = prop_info.get("type", "object")
                            if prop_info.get("format"):
                                prop_type += f"({prop_info['format']})"
                            prop_desc = prop_info.get("description", "")
                            result_text += f"         - {prop_name}: {prop_type}"
                            if prop_desc:
                                result_text += f" - {prop_desc}"
                            result_text += "\n"
                
                if request_body.get("example"):
                    example_json = json.dumps(request_body["example"], indent=2, ensure_ascii=False)
                    result_text += f"      Example:\n{_indent(example_json, 9)}\n"
            
            # Agregar responses
            responses = endpoint.get("responses")
            if responses:
                result_text += f"   Responses:\n"
                for status_code, response_info in responses.items():
                    result_text += f"      {status_code}: {response_info.get('description', '')}\n"
                    
                    schema = response_info.get("schema")
                    if schema:
                        if schema.get("schema_name"):
                            result_text += f"         Schema: {schema['schema_name']}\n"
                        if schema.get("type"):
                            result_text += f"         Type: {schema['type']}\n"
                        if schema.get("properties"):
                            result_text += f"         Properties:\n"
                            for prop_name, prop_info in schema["properties"].items():
                                prop_type = prop_info.get("type", "object")
                                result_text += f"            - {prop_name}: {prop_type}\n"
                    
                    if response_info.get("example"):
                        example_json = json.dumps(response_info["example"], indent=2, ensure_ascii=False)
                        result_text += f"         Example:\n{_indent(example_json, 12)}\n"
            
            result_text += f"   Source: {source}"
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
