import pytest
from fastapi.testclient import TestClient
from genbox.main import app
from genbox.core.config import settings

client = TestClient(app)

def test_schedule_and_delete_job():
    # 1. Schedule a job
    schedule_data = {
        "user_id": "test_user",
        "prompt": "Test prompt",
        "response_type": "text",
        "schedule_days": "Mo, Tu",
        "clock_hour": 10,
        "callback_url": "http://localhost:8000/callback"
    }
    
    headers = {"X-API-KEY": settings.API_KEY}
    
    response = client.post("/v1/schedule", json=schedule_data, headers=headers)
    
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id.startswith("test_user_")
    
    # 2. Delete the job
    delete_response = client.delete(f"/v1/schedule/{job_id}", headers=headers)
    
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"
    assert delete_response.json()["job_id"] == job_id

def test_schedule_unauthorized():
    schedule_data = {
        "user_id": "test_user",
        "prompt": "Test prompt",
        "response_type": "text",
        "schedule_days": "DD",
        "clock_hour": 10,
        "callback_url": "http://localhost:8000/callback"
    }
    
    # Send request without X-API-KEY header
    response = client.post("/v1/schedule", json=schedule_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid API key"
