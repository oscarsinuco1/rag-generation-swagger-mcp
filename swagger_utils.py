import json
import requests
import urllib3

# Deshabilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_swagger(url):
    """Descarga y parsea un Swagger JSON desde una URL."""
    response = requests.get(url, verify=False)
    response.raise_for_status()
    return response.json()


def load_swagger_from_file(filepath):
    """Carga Swagger desde archivo local."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_ref(swagger_json, ref):
    """Resuelve una referencia $ref en el Swagger."""
    if not ref or not ref.startswith("#/"):
        return None
    
    parts = ref[2:].split("/")  # Quitar "#/" y dividir
    result = swagger_json
    for part in parts:
        if isinstance(result, dict) and part in result:
            result = result[part]
        else:
            return None
    return result


def extract_schema_example(swagger_json, schema):
    """Extrae ejemplo de un schema, resolviendo referencias."""
    if not schema:
        return None
    
    # Si tiene $ref, resolver
    if "$ref" in schema:
        resolved = resolve_ref(swagger_json, schema["$ref"])
        if resolved:
            schema = resolved
        else:
            return None
    
    # Buscar example directo
    if "example" in schema:
        return schema["example"]
    
    # Generar ejemplo desde properties
    if "properties" in schema:
        example = {}
        for prop_name, prop_schema in schema["properties"].items():
            if "$ref" in prop_schema:
                resolved = resolve_ref(swagger_json, prop_schema["$ref"])
                if resolved and "example" in resolved:
                    example[prop_name] = resolved["example"]
                elif resolved:
                    example[prop_name] = extract_schema_example(swagger_json, resolved)
            elif "example" in prop_schema:
                example[prop_name] = prop_schema["example"]
            elif prop_schema.get("type") == "string":
                example[prop_name] = "string"
            elif prop_schema.get("type") == "integer":
                example[prop_name] = 0
            elif prop_schema.get("type") == "boolean":
                example[prop_name] = True
            elif prop_schema.get("type") == "array":
                example[prop_name] = []
            elif prop_schema.get("type") == "object":
                example[prop_name] = {}
        return example if example else None
    
    return None


def extract_request_body(swagger_json, details):
    """Extrae información del requestBody incluyendo ejemplos."""
    request_body = details.get("requestBody", {})
    if not request_body:
        return None
    
    content = request_body.get("content", {})
    
    # Buscar en application/json primero
    for content_type in ["application/json", "text/json", "*/*"]:
        if content_type in content:
            media = content[content_type]
            schema = media.get("schema", {})
            
            # Buscar ejemplo directo en media
            if "example" in media:
                return {
                    "content_type": content_type,
                    "example": media["example"],
                    "schema": schema
                }
            
            # Buscar examples (plural)
            if "examples" in media:
                examples = media["examples"]
                first_example = next(iter(examples.values()), {})
                if "value" in first_example:
                    return {
                        "content_type": content_type,
                        "example": first_example["value"],
                        "schema": schema
                    }
            
            # Extraer ejemplo del schema
            example = extract_schema_example(swagger_json, schema)
            if example:
                return {
                    "content_type": content_type,
                    "example": example,
                    "schema": schema
                }
            
            return {
                "content_type": content_type,
                "example": None,
                "schema": schema
            }
    
    return None


def parse_swagger(swagger_json):
    """Extrae los endpoints del Swagger en formato estructurado."""
    endpoints = []
    paths = swagger_json.get("paths", {})
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                params = []
                for param in details.get("parameters", []):
                    params.append(param.get("name", ""))
                
                # Extraer requestBody
                request_body = extract_request_body(swagger_json, details)
                
                endpoint = {
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "parameters": params,
                    "tags": details.get("tags", []),
                    "requestBody": request_body
                }
                endpoints.append(endpoint)
    
    return endpoints
