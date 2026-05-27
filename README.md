# GenBox: GenAI API & Library

**GenBox** is a unified Generative AI wrapper and scheduling engine. It provides a consistent interface for multiple providers (Gemini, OpenAI, DeepSeek, GLM, Kimi) and can be used as a standalone API or imported as a Python module.

## Features

- **3 Generation Modes**: Raw text, structured JSON (Dict), and CSV.
- **Smart Retries**: Automatic structural validation with 1-time corrective retry.
- **Multi-Provider Support**: Supports Gemini, GPT, DeepSeek, GLM, and Kimi models.
- **Persistent Caching**: SHA-256 hashed prompt caching (1h for immediate, 5h for cron).
- **Persistent Scheduling**: Schedule periodic tasks with cron-like expressions.
- **Reliable Callbacks**: Webhook callbacks with exponential backoff (2 retries over an hour).
- **Global Security**: All v1 endpoints are secured via an API Key.
- **Monitoring & KPIs**: Track success/failure, DAU, and user activity history.

## Security

All `/v1/` endpoints require an **X-API-KEY** header. Requests without this header or with an invalid key will receive a `401 Unauthorized` response.

```bash
curl -H "X-API-KEY: your_secret_key" ...
```

## Installation as a Library

To use the core logic in another Python project, install it directly from your private repository:

```bash
pip install git+https://github.com/youruser/genbox.git
```

### 1. Reusing the REST API

If you want another repository to expose the exact same endpoints (Generation, Scheduling, Monitoring) without any extra code:

**`your_new_repo/server.py`:**

```python
import uvicorn
from genbox.main import app  # Import the pre-configured FastAPI app

if __name__ == "__main__":
    # This runs all secured /v1 endpoints automatically
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Running as a Standalone API (this repo)

### Setup

1. Copy `.env.example` to `.env`.
   ```bash
   cp .env.example .env
   ```
2. Fill in your API keys and set a secure `API_KEY` for global access.

### Local Development (with Docker)

```bash
docker-compose up --build
```

The API documentation will be available at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (Use the "Authorize" button to enter your `X-API-KEY`)

### Local Development (virtualenv)

If you prefer running the application without Docker, you can use a Python virtual environment. This will run the API on the exact same port (`8000`), allowing your local Postman or cURL tests to work seamlessly.

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the virtual environment:
   - On macOS/Linux: `source venv/bin/activate`
   - On Windows: `venv\Scripts\activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   uvicorn genbox.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Local Testing (Postman / cURL)

To test the API locally after starting it with Docker:

### 1. Headers

All requests to `/v1/` endpoints **must** include this header:

- **Key**: `X-API-KEY`
- **Value**: Your `API_KEY` defined in `.env` (default is `change-me-in-production`)

### 2. Example: Raw Text Generation

- **Method**: `POST`
- **URL**: `http://localhost:8000/v1/generate/text`
- **Body (JSON)**:

```json
{
  "user_id": "test_dev",
  "prompt": "Say hello world"
}
```

### 3. Example: Structured Dict Generation
This endpoint uses a JSON schema to ensure the model returns data in the exact format you need.

**Request:**
```bash
curl -X POST http://localhost:8000/v1/generate/dict \
     -H "X-API-KEY: change-me-in-production" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "test_dev",
       "prompt": "Create a detailed book summary for The Great Gatsby.",
       "json_schema": {
         "type": "object",
         "properties": {
           "title": {"type": "string"},
           "author": {"type": "string"},
           "year": {"type": "integer"},
           "themes": {"type": "array", "items": {"type": "string"}},
           "rating": {"type": "number"}
         },
         "required": ["title", "author", "year", "themes"]
       }
     }'
```

### 4. Example: Get Monitor Stats

- **Method**: `GET`
- **URL**: `http://localhost:8000/v1/monitor/stats`
- **Headers**: Include `X-API-KEY`

## Endpoints Summary (v1)

All endpoints below require the `X-API-KEY` header.

- `POST /v1/generate/text`
- `POST /v1/generate/dict`
- `POST /v1/generate/csv`
- `POST /v1/schedule`: Cron-like periodic tasks.
- `DELETE /v1/schedule/{job_id}`: Remove a job.
- `GET /v1/monitor/stats`: Global KPIs.
- `GET /v1/monitor/logs/{user_id}`: User activity history.

## Deployment on Hetzner (Ubuntu)

1. SSH into your Hetzner Ubuntu server.
2. Install Docker and Docker-compose.
3. Clone this repository.
4. Run: `docker-compose up -d --build`
