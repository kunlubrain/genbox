import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from genbox.main import app
from genbox.core.config import settings

client = TestClient(app)

@pytest.mark.asyncio
@patch("genbox.main.genai_service.generate_text", new_callable=AsyncMock)
async def test_generate_text(mock_generate):
    mock_generate.return_value = "This is a test response."
    
    headers = {"X-API-KEY": settings.API_KEY}
    response = client.post("/v1/generate/text", json={
        "user_id": "test_user",
        "prompt": "Hello",
        "model_name": "gemini-1.5-flash"
    })
    
    assert response.status_code == 200
    assert response.json() == {"data": "This is a test response."}

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

    headers = {"X-API-KEY": settings.API_KEY}
    response = client.post("/v1/generate/dict", json={
        "user_id": "test_user",
        "prompt": "Create a bookstore inventory.",
        "json_schema": bookstore_schema
    })
    
    assert response.status_code == 200
    assert response.json()["data"]["bookstore_name"] == "Modern Reads"
    assert len(response.json()["data"]["books"]) == 2

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
    
    headers = {"X-API-KEY": settings.API_KEY}
    response = client.post("/v1/generate/csv", json={
        "user_id": "test_user",
        "prompt": prompt
    })
    
    assert response.status_code == 200
    assert len(response.json()["data"]) == 5
    assert response.json()["data"][0]["title"] == "Avatar 4"
    assert "boxoffice" in response.json()["data"][0]
