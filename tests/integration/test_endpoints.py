import os
import pytest
import vcr
from fastapi.testclient import TestClient
from genbox.main import genbox
from genbox.core.config import settings

client = TestClient(app)

# Skip if no GOOGLE_API_KEY is found (using Gemini as our test case)
skip_if_no_api_key = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY") and not settings.GOOGLE_API_KEY,
    reason="GOOGLE_API_KEY is not set in environment"
)

# Configure VCR to filter out sensitive info and handle async
my_vcr = vcr.VCR(
    serializer='yaml',
    cassette_library_dir='tests/integration/cassettes',
    record_mode='once',
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query'],
    filter_headers=['authorization', 'x-goog-api-key'],
)

@pytest.mark.asyncio
@skip_if_no_api_key
@my_vcr.use_cassette('test_generate_text_real.yaml')
async def test_generate_text_real():
    headers = {"X-API-KEY": settings.API_KEY}
    response = client.post("/v1/generate/text", json={
        "user_id": "test_user",
        "prompt": "Say 'Integration test success' in one short sentence.",
        "model_name": "gemini-1.5-flash"
    })
    
    assert response.status_code == 200
    assert "data" in response.json()
    assert len(response.json()["data"]) > 0

@pytest.mark.asyncio
@skip_if_no_api_key
@my_vcr.use_cassette('test_generate_dict_bookstore_real.yaml')
async def test_generate_dict_bookstore_real():
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
        "prompt": "Create a bookstore inventory with 2 books about Python.",
        "json_schema": bookstore_schema,
        "model_name": "gemini-1.5-flash"
    })
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert "bookstore_name" in data
    assert len(data["books"]) >= 2
    assert isinstance(data["books"][0]["price"], (int, float))

@pytest.mark.asyncio
@skip_if_no_api_key
@my_vcr.use_cassette('test_generate_csv_movies_real.yaml')
async def test_generate_csv_movies_real():
    prompt = "List 5 movies in 2026 with title, country, genre, imgurl, boxoffice as CSV."
    
    headers = {"X-API-KEY": settings.API_KEY}
    response = client.post("/v1/generate/csv", json={
        "user_id": "test_user",
        "prompt": prompt,
        "model_name": "gemini-1.5-flash"
    })
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 5
    first_movie = data[0]
    required_cols = ["title", "country", "genre", "imgurl", "boxoffice"]
    for col in required_cols:
        assert col in first_movie
