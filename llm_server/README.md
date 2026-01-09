# Local LLM Server

A FastAPI service that provides local LLM inference using HuggingFace transformers. This service allows you to run language models locally without sending data to external APIs.

## Features

- FastAPI-based REST API for LLM queries
- Basic authentication for security
- HuggingFace transformers integration
- Configurable model selection
- Docker containerization with persistent model caching
- Health check endpoints

## Quick Start

### Using Docker Compose

1. Set your credentials in `.env`:
```bash
LLM_USERNAME=your_username
LLM_PASSWORD=your_password
LLM_MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0  # optional, this is the default
```

2. Start the service:
```bash
docker-compose up llm-server
```

**Note:** The first build will take longer as it downloads dependencies and the model. Subsequent builds will be faster.

3. Wait for the model to download and load (first run takes a few minutes)

4. Test the service:
```bash
curl -X GET http://localhost:8000/health
```

### Making Queries

Once the service is running, you can make queries using basic authentication:

```bash
curl -X POST http://localhost:8000/query \
  -u "your_username:your_password" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the capital of France?",
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

Python example:
```python
import requests
from requests.auth import HTTPBasicAuth

response = requests.post(
    "http://localhost:8000/query",
    auth=HTTPBasicAuth("your_username", "your_password"),
    json={
        "prompt": "What is the capital of France?",
        "max_tokens": 100,
        "temperature": 0.7,
        "top_p": 0.95,
    }
)

result = response.json()
print(result["response"])
```

## API Endpoints

### GET /
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "Local LLM Service",
  "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
}
```

### GET /health
Detailed health check with model status.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
}
```

### POST /query
Query the LLM with a prompt (requires authentication).

**Request:**
```json
{
  "prompt": "Your question or prompt here",
  "max_tokens": 512,
  "temperature": 0.7,
  "top_p": 0.95
}
```

**Response:**
```json
{
  "response": "Generated text from the model",
  "model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
  "prompt": "Your original prompt"
}
```

## Configuration

### Environment Variables

- `LLM_USERNAME`: Username for basic authentication (default: `admin`)
- `LLM_PASSWORD`: Password for basic authentication (default: `password`)
- `MODEL_NAME`: HuggingFace model to use (default: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`)
- `PORT`: Port to run the service on (default: `8000`)

### Changing Models

To use a different model, set the `LLM_MODEL_NAME` environment variable to any compatible HuggingFace model:

```bash
# Small models for testing (1-3GB)
LLM_MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0
LLM_MODEL_NAME=microsoft/phi-2

# Medium models (7-13GB) - requires more RAM
LLM_MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
LLM_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.2
```

**Note:** Larger models require more RAM and disk space. Make sure your system has sufficient resources.

## Development

### Local Development

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies:
```bash
cd llm_server
uv sync
```

3. Set environment variables:
```bash
export LLM_USERNAME=admin
export LLM_PASSWORD=password
export MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

4. Run the server:
```bash
uv run python main.py
```

Or with uvicorn:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Adding Dependencies

To add new dependencies, edit `pyproject.toml` and add the package to the `dependencies` list, then run:
```bash
uv sync
```

### Testing

Test the authentication:
```bash
# Should fail with 401
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'

# Should succeed
curl -X POST http://localhost:8000/query \
  -u "admin:password" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'
```

## Architecture

The service uses:
- **FastAPI** for the web framework
- **HuggingFace Transformers** for model loading and inference
- **PyTorch** as the ML backend
- **HTTP Basic Auth** for authentication
- **Docker volumes** for persistent model caching

Models are downloaded once and cached in a Docker volume, so subsequent restarts are much faster.

## Performance Considerations

- First startup downloads the model (can take 5-15 minutes depending on model size and connection speed)
- Subsequent startups are much faster (10-30 seconds) as models are cached
- TinyLlama (1.1B parameters) can run on CPU with ~4GB RAM
- Larger models (7B+) benefit significantly from GPU acceleration
- Generation speed varies by model size and hardware

## Security

- Basic authentication is enabled by default
- Change the default username and password in production
- The service runs on localhost:8000 by default
- For production use, consider adding:
  - HTTPS/TLS
  - More robust authentication (JWT, OAuth)
  - Rate limiting
  - Request logging and monitoring

## Troubleshooting

### Model not loading
- Check available disk space (models can be several GB)
- Check available RAM (minimum 4GB for small models)
- Verify the model name exists on HuggingFace

### Out of memory errors
- Use a smaller model
- Reduce `max_tokens` in queries
- Ensure no other memory-intensive processes are running

### Slow generation
- This is expected on CPU for larger models
- Consider using a smaller model for CPU inference
- Use GPU acceleration if available

## License

MIT
