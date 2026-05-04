"""
Servidor HTTP para probar el RAG de Swagger sin necesidad de MCP.
"""
import os
import json
import threading
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from vector_store import get_collection, search

COLLECTION_NAME = "swagger_rag"

app = FastAPI(title="Swagger RAG API", description="API para buscar endpoints en Swagger")

# Variable global para la colección
_coleccion = None


def get_coleccion():
    """Obtiene la colección de ChromaDB."""
    global _coleccion
    if _coleccion is None:
        _coleccion = get_collection(collection_name=COLLECTION_NAME)
    return _coleccion


@app.get("/", response_class=HTMLResponse)
async def home():
    """Página principal con interfaz de búsqueda."""
    return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Swagger RAG - Búsqueda Semántica</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #333; }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
        }
        input[type="text"]:focus {
            border-color: #007bff;
            outline: none;
        }
        button {
            padding: 12px 24px;
            font-size: 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        button:hover { background: #0056b3; }
        button:disabled { background: #ccc; }
        .results {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .endpoint {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .endpoint-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }
        .method {
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
            color: white;
        }
        .method.GET { background: #28a745; }
        .method.POST { background: #007bff; }
        .method.PUT { background: #ffc107; color: #333; }
        .method.DELETE { background: #dc3545; }
        .method.PATCH { background: #17a2b8; }
        .path {
            font-family: monospace;
            font-size: 16px;
            color: #333;
        }
        .summary { color: #666; margin-bottom: 10px; }
        .section {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        .section-title {
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
        }
        .params, .schema {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
            overflow-x: auto;
        }
        .param {
            margin: 5px 0;
        }
        .param-name { color: #007bff; }
        .param-type { color: #28a745; }
        .param-required { color: #dc3545; }
        pre {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 12px;
        }
        .stats {
            color: #666;
            margin-bottom: 15px;
        }
        .source {
            font-size: 12px;
            color: #999;
            margin-top: 10px;
        }
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 10px;
        }
        .tab {
            padding: 5px 10px;
            background: #eee;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }
        .tab.active { background: #007bff; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .response-code {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            margin-right: 8px;
        }
        .response-code.success { background: #d4edda; color: #155724; }
        .response-code.error { background: #f8d7da; color: #721c24; }
        .response-code.default { background: #e2e3e5; color: #383d41; }
    </style>
</head>
<body>
    <h1>🔍 Swagger RAG - Búsqueda Semántica</h1>
    
    <div class="search-box">
        <input type="text" id="query" placeholder="Describe lo que buscas... ej: 'crear usuario', 'obtener mascota por id'" autofocus>
        <input type="number" id="nResults" value="5" min="1" max="20" style="width: 80px;">
        <button onclick="searchEndpoints()">Buscar</button>
        <button onclick="listAll()" style="background: #6c757d;">Listar todos</button>
    </div>
    
    <div id="stats" class="stats"></div>
    <div id="results" class="results"></div>

    <script>
        document.getElementById('query').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchEndpoints();
        });

        async function searchEndpoints() {
            const query = document.getElementById('query').value;
            const nResults = document.getElementById('nResults').value;
            if (!query) return;
            
            document.getElementById('results').innerHTML = '<p>Buscando...</p>';
            
            try {
                const res = await fetch(`/api/search?query=${encodeURIComponent(query)}&n_results=${nResults}`);
                const data = await res.json();
                renderResults(data.results, data.count, query);
            } catch (err) {
                document.getElementById('results').innerHTML = `<p style="color:red">Error: ${err.message}</p>`;
            }
        }

        async function listAll() {
            document.getElementById('results').innerHTML = '<p>Cargando...</p>';
            
            try {
                const res = await fetch('/api/list');
                const data = await res.json();
                renderResults(data.results, data.count, null);
            } catch (err) {
                document.getElementById('results').innerHTML = `<p style="color:red">Error: ${err.message}</p>`;
            }
        }

        function renderResults(results, count, query) {
            document.getElementById('stats').textContent = query 
                ? `${count} resultado(s) para "${query}"`
                : `${count} endpoint(s) indexados`;
            
            if (!results || results.length === 0) {
                document.getElementById('results').innerHTML = '<p>No se encontraron resultados.</p>';
                return;
            }
            
            const html = results.map((ep, idx) => renderEndpoint(ep, idx)).join('');
            document.getElementById('results').innerHTML = html;
        }

        function renderEndpoint(ep, idx) {
            let html = `
                <div class="endpoint">
                    <div class="endpoint-header">
                        <span class="method ${ep.method}">${ep.method}</span>
                        <span class="path">${ep.path}</span>
                    </div>
                    <div class="summary">${ep.summary || 'Sin descripción'}</div>
            `;
            
            // Parámetros
            if (ep.parameters && ep.parameters.length > 0) {
                html += `<div class="section">
                    <div class="section-title">Parámetros</div>
                    <div class="params">`;
                ep.parameters.forEach(p => {
                    const req = p.required ? '<span class="param-required">*</span>' : '';
                    html += `<div class="param">
                        <span class="param-name">${p.name}</span>${req}
                        (<span class="param-type">${p.type || 'string'}</span>, ${p.in})
                        ${p.description ? '- ' + p.description : ''}
                        ${p.enum ? '<br>Valores: ' + p.enum.join(', ') : ''}
                    </div>`;
                });
                html += `</div></div>`;
            }
            
            // Request Body
            if (ep.requestBody) {
                html += `<div class="section">
                    <div class="section-title">Request Body ${ep.requestBody.required ? '(requerido)' : ''}</div>`;
                
                if (ep.requestBody.schema) {
                    const schema = ep.requestBody.schema;
                    if (schema.schema_name) {
                        html += `<p>Schema: <strong>${schema.schema_name}</strong></p>`;
                    }
                    if (schema.required) {
                        html += `<p>Campos requeridos: <code>${schema.required.join(', ')}</code></p>`;
                    }
                    if (schema.properties) {
                        html += `<div class="params">`;
                        for (const [name, prop] of Object.entries(schema.properties)) {
                            const type = prop.format ? `${prop.type}(${prop.format})` : prop.type;
                            html += `<div class="param">
                                <span class="param-name">${name}</span>: 
                                <span class="param-type">${type || 'object'}</span>
                                ${prop.description ? '- ' + prop.description : ''}
                                ${prop.enum ? '<br>Valores: ' + prop.enum.join(', ') : ''}
                            </div>`;
                        }
                        html += `</div>`;
                    }
                }
                
                if (ep.requestBody.example) {
                    html += `<details><summary>Ejemplo</summary><pre>${JSON.stringify(ep.requestBody.example, null, 2)}</pre></details>`;
                }
                html += `</div>`;
            }
            
            // Responses
            if (ep.responses) {
                html += `<div class="section">
                    <div class="section-title">Respuestas</div>`;
                
                for (const [code, resp] of Object.entries(ep.responses)) {
                    const codeClass = code.startsWith('2') ? 'success' : (code.startsWith('4') || code.startsWith('5') ? 'error' : 'default');
                    html += `<div style="margin: 10px 0;">
                        <span class="response-code ${codeClass}">${code}</span>
                        ${resp.description || ''}
                    `;
                    
                    if (resp.schema) {
                        if (resp.schema.schema_name) {
                            html += ` - Schema: <strong>${resp.schema.schema_name}</strong>`;
                        }
                        if (resp.schema.properties) {
                            html += `<details><summary>Propiedades</summary><div class="params">`;
                            for (const [name, prop] of Object.entries(resp.schema.properties)) {
                                const type = prop.format ? `${prop.type}(${prop.format})` : prop.type;
                                html += `<div class="param">
                                    <span class="param-name">${name}</span>: 
                                    <span class="param-type">${type || 'object'}</span>
                                    ${prop.description ? '- ' + prop.description : ''}
                                </div>`;
                            }
                            html += `</div></details>`;
                        }
                    }
                    
                    if (resp.example) {
                        html += `<details><summary>Ejemplo</summary><pre>${JSON.stringify(resp.example, null, 2)}</pre></details>`;
                    }
                    html += `</div>`;
                }
                html += `</div>`;
            }
            
            html += `<div class="source">Fuente: ${ep.source_url || 'N/A'}</div>`;
            html += `</div>`;
            
            return html;
        }
    </script>
</body>
</html>
"""


@app.get("/api/search")
async def api_search(query: str = Query(..., description="Búsqueda semántica"), 
                     n_results: int = Query(5, ge=1, le=50)):
    """Busca endpoints por descripción semántica."""
    coleccion = get_coleccion()
    
    if coleccion.count() == 0:
        return JSONResponse({"results": [], "count": 0, "error": "No hay endpoints indexados"})
    
    resultados = search(coleccion, query, n_results=n_results)
    
    endpoints = [json.loads(doc) for doc in resultados]
    return {"results": endpoints, "count": len(endpoints), "query": query}


@app.get("/api/list")
async def api_list():
    """Lista todos los endpoints indexados."""
    coleccion = get_coleccion()
    all_docs = coleccion.get()
    
    if not all_docs['documents']:
        return {"results": [], "count": 0}
    
    endpoints = [json.loads(doc) for doc in all_docs['documents']]
    return {"results": endpoints, "count": len(endpoints)}


@app.get("/api/stats")
async def api_stats():
    """Estadísticas de la colección."""
    coleccion = get_coleccion()
    count = coleccion.count()
    
    # Agrupar por source
    all_docs = coleccion.get()
    sources = {}
    for doc in all_docs.get('documents', []):
        ep = json.loads(doc)
        source = ep.get('source_url', 'unknown')
        sources[source] = sources.get(source, 0) + 1
    
    return {
        "total_endpoints": count,
        "sources": sources
    }


def start_http_server(host: str = "0.0.0.0", port: int = 8080):
    """Inicia el servidor HTTP en un thread separado."""
    def run():
        uvicorn.run(app, host=host, port=port, log_level="warning")
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
