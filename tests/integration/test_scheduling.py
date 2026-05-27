import pytest
from fastapi.testclient import TestClient
from genbox.main import app
from genbox.core.security import get_api_key

client = TestClient(app)

# Use a dummy token for all tests
TEST_TOKEN = "test-token-only-for-tests"

async def mock_get_api_key():
    return TEST_TOKEN

@pytest.fixture
def authorized_client():
    app.dependency_overrides[get_api_key] = mock_get_api_key
    yield client
    app.dependency_overrides = {}

def test_schedule_and_delete_job(authorized_client):
    # 1. Schedule a job
    schedule_data = {
        "user_id": "test_user",
        "prompt": "Test prompt",
        "response_type": "text",
        "schedule_days": "Mo, Tu",
        "clock_hour": 10,
        "callback_url": "http://localhost:8000/callback"
    }
    
    headers = {"X-API-KEY": TEST_TOKEN}
    response = authorized_client.post("/v1/schedule", json=schedule_data, headers=headers)
    
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    # 2. Delete the job
    delete_response = authorized_client.delete(f"/v1/schedule/{job_id}", headers=headers)
    
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

def test_schedule_unauthorized():
    # Do NOT use the authorized fixture here
    schedule_data = {
        "user_id": "test_user",
        "prompt": "Test prompt",
        "response_type": "text",
        "schedule_days": "DD",
        "clock_hour": 10,
        "callback_url": "http://localhost:8000/callback"
    }
    
    # Send request without valid header
    response = client.post("/v1/schedule", json=schedule_data, headers={"X-API-KEY": "wrong-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid access token"
