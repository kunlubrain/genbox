import os
import pytest
import vcr
from fastapi.testclient import TestClient
from genbox.main import app
from genbox.core.security import get_api_key

client = TestClient(app)

TEST_TOKEN = "test-token-integration"

async def mock_get_api_key():
    return TEST_TOKEN

@pytest.fixture(autouse=True)
def setup_security_override():
    app.dependency_overrides[get_api_key] = mock_get_api_key
    yield
    app.dependency_overrides = {}

# Skip if no GOOGLE_API_KEY is found
skip_if_no_api_key = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY is not set in environment"
)

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
    headers = {"X-API-KEY": TEST_TOKEN}
    response = client.post("/v1/generate/text", json={
        "user_id": "test_user",
        "prompt": "Say 'Integration test success' in one short sentence.",
        "model_name": "gemini-1.5-flash"
    }, headers=headers)
    
    assert response.status_code == 200
    assert "data" in response.json()

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

    headers = {"X-API-KEY": TEST_TOKEN}
    response = client.post("/v1/generate/dict", json={
        "user_id": "test_user",
        "prompt": "Create a bookstore inventory with 2 books about Python.",
        "json_schema": bookstore_schema,
        "model_name": "gemini-1.5-flash"
    }, headers=headers)
    
    assert response.status_code == 200

@pytest.mark.asyncio
@skip_if_no_api_key
@my_vcr.use_cassette('test_generate_csv_movies_real.yaml')
async def test_generate_csv_movies_real():
    prompt = "List 5 movies in 2026 with title, country, genre, imgurl, boxoffice as CSV."
    
    headers = {"X-API-KEY": TEST_TOKEN}
    response = client.post("/v1/generate/csv", json={
        "user_id": "test_user",
        "prompt": prompt,
        "model_name": "gemini-1.5-flash"
    }, headers=headers)
    
    assert response.status_code == 200
