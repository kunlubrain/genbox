import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from genbox.main import app
from genbox.core.config import settings
from genbox.core.security import get_api_key
from genbox.services.monitoring_service import monitor_service

client = TestClient(app)

# Bypass security for unit tests
async def override_get_api_key():
    return "test-key"

@pytest.fixture(autouse=True)
def setup_dependency_overrides():
    app.dependency_overrides[get_api_key] = override_get_api_key
    yield
    app.dependency_overrides = {}

# Mock monitor_service globally for unit tests to avoid DB/Cache hits
@pytest.fixture(autouse=True)
def mock_monitor():
    with patch("genbox.main.monitor_service.get_cached_response", return_value=None), \
         patch("genbox.main.monitor_service.log_request", return_value=None):
        yield

@pytest.mark.asyncio
@patch("genbox.main.genai_service.generate_text", new_callable=AsyncMock)
async def test_generate_text(mock_generate):
    mock_generate.return_value = "This is a test response."
    
    headers = {"X-API-KEY": "any-valid-token"}
    response = client.post("/v1/generate/text", json={
        "user_id": "test_user",
        "prompt": "Hello",
        "model_name": "gemini-1.5-flash"
    }, headers=headers)
    
    assert response.status_code == 200
    assert response.json() == {"data": "This is a test response."}
    mock_generate.assert_called_once()

@pytest.mark.asyncio
@patch("genbox.main.genai_service.generate_dict", new_callable=AsyncMock)
async def test_generate_dict_bookstore(mock_generate):
    # Mock data matching the bookstore schema
    mock_data = {
        "bookstore_name": "Modern Reads",
        "books": [
            {"title": "The AI Revolution", "author": "John Doe", "price": 29.99},
            {"title": "FastAPI Masterclass", "author": "Jane Smith", "price": 34.50}
        ]
    }
    mock_generate.return_value = mock_data
    
    bookstore_schema = {
        "type": "object",
        "properties": {
            "bookstore_name": {"type": "string"},
            "books": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "author": {"type": "string"},
                        "price": {"type": "number"}
                    },
                    "required": ["title", "author", "price"]
                }
            }
        },
        "required": ["bookstore_name", "books"]
    }

    headers = {"X-API-KEY": "any-valid-token"}
    response = client.post("/v1/generate/dict", json={
        "user_id": "test_user",
        "prompt": "Create a bookstore inventory.",
        "json_schema": bookstore_schema
    }, headers=headers)
    
    assert response.status_code == 200
    assert response.json()["data"]["bookstore_name"] == "Modern Reads"
    assert len(response.json()["data"]["books"]) == 2
    mock_generate.assert_called_once()

@pytest.mark.asyncio
@patch("genbox.main.genai_service.generate_csv", new_callable=AsyncMock)
async def test_generate_csv_movies(mock_generate):
    # Mock data matching the requested CSV structure
    mock_data = [
        {"title": "Avatar 4", "country": "USA", "genre": "Sci-Fi", "imgurl": "http://example.com/a4.jpg", "boxoffice": "2.5B"},
        {"title": "The Batman II", "country": "USA", "genre": "Action", "imgurl": "http://example.com/b2.jpg", "boxoffice": "1.2B"},
        {"title": "Dune: Part Three", "country": "USA", "genre": "Sci-Fi", "imgurl": "http://example.com/d3.jpg", "boxoffice": "1.0B"},
        {"title": "Beyond the Spider-Verse", "country": "USA", "genre": "Animation", "imgurl": "http://example.com/sp.jpg", "boxoffice": "1.1B"},
        {"title": "Untitled Marvel Movie", "country": "USA", "genre": "Action", "imgurl": "http://example.com/m.jpg", "boxoffice": "1.5B"}
    ]
    mock_generate.return_value = mock_data
    
    prompt = "List 5 movies in 2026 with title, country, genre, imgurl, boxoffice as CSV."
    
    headers = {"X-API-KEY": "any-valid-token"}
    response = client.post("/v1/generate/csv", json={
        "user_id": "test_user",
        "prompt": prompt
    }, headers=headers)
    
    assert response.status_code == 200
    assert len(response.json()["data"]) == 5
    assert response.json()["data"][0]["title"] == "Avatar 4"
    mock_generate.assert_called_once()
