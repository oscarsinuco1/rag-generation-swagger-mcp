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


def extract_schema_details(swagger_json, schema, depth=0):
    """Extrae detalles completos de un schema incluyendo tipos y required."""
    if not schema or depth > 5:  # Evitar recursión infinita
        return None
    
    # Si tiene $ref, resolver
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        resolved = resolve_ref(swagger_json, schema["$ref"])
        if resolved:
            schema = resolved
            schema["_ref_name"] = ref_name
        else:
            return {"$ref": schema["$ref"]}
    
    result = {}
    
    # Copiar atributos básicos
    if "_ref_name" in schema:
        result["schema_name"] = schema["_ref_name"]
    if "type" in schema:
        result["type"] = schema["type"]
    if "format" in schema:
        result["format"] = schema["format"]
    if "description" in schema:
        result["description"] = schema["description"]
    if "enum" in schema:
        result["enum"] = schema["enum"]
    if "required" in schema:
        result["required"] = schema["required"]
    if "example" in schema:
        result["example"] = schema["example"]
    
    # Procesar properties
    if "properties" in schema:
        result["properties"] = {}
        for prop_name, prop_schema in schema["properties"].items():
            prop_details = {
                "type": prop_schema.get("type", "object"),
            }
            if "format" in prop_schema:
                prop_details["format"] = prop_schema["format"]
            if "description" in prop_schema:
                prop_details["description"] = prop_schema["description"]
            if "enum" in prop_schema:
                prop_details["enum"] = prop_schema["enum"]
            if "example" in prop_schema:
                prop_details["example"] = prop_schema["example"]
            
            # Resolver $ref en properties
            if "$ref" in prop_schema:
                resolved = resolve_ref(swagger_json, prop_schema["$ref"])
                if resolved:
                    prop_details = extract_schema_details(swagger_json, resolved, depth + 1) or prop_details
                    prop_details["$ref"] = prop_schema["$ref"].split("/")[-1]
            
            result["properties"][prop_name] = prop_details
    
    # Procesar items (para arrays)
    if "items" in schema:
        result["items"] = extract_schema_details(swagger_json, schema["items"], depth + 1)
    
    return result


def extract_responses(swagger_json, details):
    """Extrae información de las respuestas incluyendo schemas."""
    responses = details.get("responses", {})
    if not responses:
        return None
    
    result = {}
    for status_code, response_info in responses.items():
        response_data = {
            "description": response_info.get("description", "")
        }
        
        content = response_info.get("content", {})
        for content_type in ["application/json", "text/json", "application/xml", "*/*"]:
            if content_type in content:
                media = content[content_type]
                schema = media.get("schema", {})
                
                response_data["content_type"] = content_type
                response_data["schema"] = extract_schema_details(swagger_json, schema)
                
                # Extraer ejemplo
                if "example" in media:
                    response_data["example"] = media["example"]
                elif "examples" in media:
                    examples = media["examples"]
                    first_example = next(iter(examples.values()), {})
                    if "value" in first_example:
                        response_data["example"] = first_example["value"]
                else:
                    response_data["example"] = extract_schema_example(swagger_json, schema)
                
                break
        
        result[status_code] = response_data
    
    return result


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
            schema_details = extract_schema_details(swagger_json, schema)
            
            # Buscar ejemplo directo en media
            if "example" in media:
                return {
                    "content_type": content_type,
                    "example": media["example"],
                    "schema": schema_details,
                    "required": request_body.get("required", False)
                }
            
            # Buscar examples (plural)
            if "examples" in media:
                examples = media["examples"]
                first_example = next(iter(examples.values()), {})
                if "value" in first_example:
                    return {
                        "content_type": content_type,
                        "example": first_example["value"],
                        "schema": schema_details,
                        "required": request_body.get("required", False)
                    }
            
            # Extraer ejemplo del schema
            example = extract_schema_example(swagger_json, schema)
            return {
                "content_type": content_type,
                "example": example,
                "schema": schema_details,
                "required": request_body.get("required", False)
            }
    
    return None


def parse_swagger(swagger_json):
    """Extrae los endpoints del Swagger en formato estructurado."""
    endpoints = []
    paths = swagger_json.get("paths", {})
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                # Extraer parámetros con detalles
                params = []
                for param in details.get("parameters", []):
                    param_info = {
                        "name": param.get("name", ""),
                        "in": param.get("in", ""),  # query, path, header, cookie
                        "required": param.get("required", False),
                        "type": param.get("schema", {}).get("type", param.get("type", "string")),
                        "description": param.get("description", "")
                    }
                    if "enum" in param.get("schema", {}):
                        param_info["enum"] = param["schema"]["enum"]
                    if "format" in param.get("schema", {}):
                        param_info["format"] = param["schema"]["format"]
                    params.append(param_info)
                
                # Extraer requestBody
                request_body = extract_request_body(swagger_json, details)
                
                # Extraer responses
                responses = extract_responses(swagger_json, details)
                
                endpoint = {
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "parameters": params,
                    "tags": details.get("tags", []),
                    "requestBody": request_body,
                    "responses": responses
                }
                endpoints.append(endpoint)
    
    return endpoints
