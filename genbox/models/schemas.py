from pydantic import BaseModel
from typing import Any
from datetime import datetime

class GenerateRequest(BaseModel):
    user_id: str
    prompt: str
    model_name: str | None = None
    json_schema: dict[str, Any] | None = None

class ScheduleRequest(BaseModel):
    user_id: str
    prompt: str
    model_name: str | None = None
    response_type: str = "text"
    json_schema: dict[str, Any] | None = None
    schedule_days: str = "Su"
    clock_hour: int = 1
    end_date: datetime | None = None
    callback_url: str

class GenerateResponse(BaseModel):
    data: Any

class JobInfo(BaseModel):
    job_id: str
    status: str

class MonitorStats(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    dau: int
    cron_requests_today: int

class LogEntry(BaseModel):
    id: int
    prompt: str
    timestamp: datetime
    status: str
    periodicity: str
    job_id: str | None

class UserLogsResponse(BaseModel):
    user_id: str
    logs: list[LogEntry]
