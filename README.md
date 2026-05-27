# GenBox: GenAI API & Library

**GenBox** is a unified Generative AI wrapper and scheduling engine. It provides a consistent interface for multiple providers (Gemini, OpenAI, DeepSeek, GLM, Kimi) and can be used as a standalone API or imported as a Python module.

## Features
- **3 Generation Modes**: Raw text, structured JSON (Dict), and CSV.
- **Smart Retries**: Automatic structural validation with 1-time corrective retry.
- **Multi-Provider Support**: Supports Gemini, GPT, DeepSeek, GLM, and Kimi models.
- **Persistent Caching**: SHA-256 hashed prompt caching (1h for immediate, 5h for cron).
- **Persistent Scheduling**: Schedule periodic tasks with cron-like expressions.
- **Reliable Callbacks**: Webhook callbacks with exponential backoff (2 retries over an hour).
- **Multi-Token Security**: Access is restricted to authorized tokens managed in your environment.
- **Monitoring & KPIs**: Track success/failure, DAU, and user activity history.

## Security

Access to **all** `/v1/` endpoints is secured via a mandatory access token. You must provide a valid token in the `X-API-KEY` header.

**Note:** These are *your* service tokens defined in the `.env` file (via `AUTHORIZED_TOKENS_STR`). You never need to provide individual LLM provider keys in the request; those are managed internally by the server.

```bash
curl -H "X-API-KEY: your_service_token_here" ...
```

## Installation as a Library

To use the core logic in another Python project, install it directly from your private repository:

```bash
pip install git+https://github.com/youruser/genbox.git
```

### 1. Reusing the REST API
If you want another repository to expose the exact same endpoints:

**`your_new_repo/server.py`:**
```python
import uvicorn
from genbox.main import app  # Import the pre-configured FastAPI app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Running as a Standalone API (this repo)

### Setup
1. Copy `.env.example` to `.env`.
   ```bash
   cp .env.example .env
   ```
2. Fill in your LLM API keys (Gemini, etc.) and define your access tokens in `AUTHORIZED_TOKENS_STR`.

### Local Development (with Docker)
```bash
docker-compose up --build
```
The API documentation will be available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (Use the "Authorize" button to enter one of your access tokens)

## Local Testing (Postman / cURL)

### 1. Headers
All requests to `/v1/` endpoints **must** include this header:
- **Key**: `X-API-KEY`
- **Value**: One of the tokens defined in your `AUTHORIZED_TOKENS_STR`

### 2. Example: Structured Dict Generation
```bash
curl -X POST http://localhost:8000/v1/generate/dict \
     -H "X-API-KEY: token1_secret" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "test_dev",
       "prompt": "Create a detailed book summary for The Great Gatsby.",
       "json_schema": {
         "type": "object",
         "properties": {
           "title": {"type": "string"},
           "author": {"type": "string"},
           "year": {"type": "integer"}
         },
         "required": ["title", "author", "year"]
       }
     }'
```

## Deployment on Hetzner (Ubuntu)

1. SSH into your Hetzner Ubuntu server.
2. Install Docker and Docker-compose.
3. Clone this repository.
4. Run: `docker-compose up -d --build`
