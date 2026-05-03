# Swagger RAG MCP Server

MCP (Model Context Protocol) server that provides semantic search over Swagger/OpenAPI endpoints. Uses vector embeddings to find relevant API endpoints based on natural language queries.

## Features

- **Semantic Search**: Find API endpoints by describing what you need in natural language
- **Multi-Swagger Support**: Index multiple Swagger files simultaneously
- **Lightweight**: Uses ONNX-based embeddings via fastembed (~1.2GB Docker image)
- **Multilingual**: Supports queries in multiple languages (Spanish, English, etc.)

## Quick Start

### Docker Hub

```bash
docker pull oscarsinuco/swagger-rag-mcp:latest
```

### VS Code MCP Configuration

Add to your `mcp.json`:

```json
{
  "servers": {
    "swagger-rag": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/swagger-urls.txt:/app/urls.txt:ro",
        "oscarsinuco/swagger-rag-mcp:latest"
      ]
    }
  }
}
```

### URL File Format

Create a `swagger-urls.txt` file with one Swagger URL per line:

```
https://petstore.swagger.io/v2/swagger.json
https://api.example.com/swagger/v1/swagger.json
# Comments start with #
```

## Available Tools

### `search_endpoint`

Search for endpoints by semantic description.

**Parameters:**
- `query` (required): Natural language description of the endpoint you're looking for
- `n_results` (optional): Number of results to return (default: 3)

**Example:**
```
query: "create a new user"
```

### `list_all_endpoints`

Lists all indexed endpoints from all Swagger files.

## Building from Source

```bash
# Clone the repository
git clone https://github.com/oscarsinuco1/rag-generation-swagger-mcp.git
cd rag-generation-swagger-mcp

# Build Docker image
docker build -t swagger-rag-mcp:latest .

# Or with HuggingFace token for faster model download
docker build --build-arg HF_TOKEN=your_token -t swagger-rag-mcp:latest .
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   VS Code +     │────▶│  MCP Server      │────▶│   ChromaDB      │
│   Copilot       │◀────│  (stdio)         │◀────│   (in-memory)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   FastEmbed      │
                        │   (ONNX model)   │
                        └──────────────────┘
```

## Model

Uses `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`:
- 384-dimensional embeddings
- Multilingual support (50+ languages)
- ONNX runtime for fast inference

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EMBEDDING_MODEL` | Model name for embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| `SWAGGER_URLS_FILE` | Path to URLs file inside container | `/app/urls.txt` |

## License

MIT
