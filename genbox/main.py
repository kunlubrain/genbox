import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from genbox.models.schemas import GenerateRequest, GenerateResponse, ScheduleRequest, JobInfo, MonitorStats, UserLogsResponse, LogEntry
from genbox.services.genai_service import genai_service
from genbox.services.scheduler_service import scheduler_service
from genbox.services.monitoring_service import monitor_service
from genbox.core.config import settings
from genbox.core.security import get_api_key

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the scheduler
    scheduler_service.start()
    yield
    # Shutdown: Stop the scheduler
    scheduler_service.shutdown()

app = FastAPI(
    title="GenBox API",
    version="1.5.1",
    description="Secure unified API for GenAI providers with scheduling and monitoring.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Create a versioned router that requires API Key authentication
v1_router = APIRouter(prefix="/v1", dependencies=[Depends(get_api_key)])

# --- Generation Endpoints ---

@v1_router.post("/generate/text", response_model=GenerateResponse)
async def generate_text_endpoint(request: GenerateRequest):
    try:
        cached_data = monitor_service.get_cached_response(request.prompt, is_cron=False)
        if cached_data is not None:
            return GenerateResponse(data=cached_data)

        data = await genai_service.generate_text(request.prompt, request.model_name)
        monitor_service.log_request(request.user_id, request.prompt, "success", response_data=data)
        return GenerateResponse(data=data)
    except Exception as e:
        monitor_service.log_request(request.user_id, request.prompt, "failed")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.post("/generate/dict", response_model=GenerateResponse)
async def generate_dict_endpoint(request: GenerateRequest):
    try:
        cached_data = monitor_service.get_cached_response(request.prompt, is_cron=False)
        if cached_data is not None:
            return GenerateResponse(data=cached_data)

        data = await genai_service.generate_dict(request.prompt, request.model_name, json_schema=request.json_schema)
        monitor_service.log_request(request.user_id, request.prompt, "success", response_data=data)
        return GenerateResponse(data=data)
    except Exception as e:
        monitor_service.log_request(request.user_id, request.prompt, "failed")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.post("/generate/csv", response_model=GenerateResponse)
async def generate_csv_endpoint(request: GenerateRequest):
    try:
        cached_data = monitor_service.get_cached_response(request.prompt, is_cron=False)
        if cached_data is not None:
            return GenerateResponse(data=cached_data)

        data = await genai_service.generate_csv(request.prompt, request.model_name)
        monitor_service.log_request(request.user_id, request.prompt, "success", response_data=data)
        return GenerateResponse(data=data)
    except Exception as e:
        monitor_service.log_request(request.user_id, request.prompt, "failed")
        raise HTTPException(status_code=500, detail=str(e))


# --- Scheduling Endpoints ---

@v1_router.post("/schedule", response_model=JobInfo)
async def schedule_job_endpoint(request: ScheduleRequest):
    try:
        job_id = await scheduler_service.schedule_job(request)
        return JobInfo(job_id=job_id, status="scheduled")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.delete("/schedule/{job_id}")
async def delete_job_endpoint(job_id: str):
    try:
        scheduler_service.delete_job(job_id)
        return {"status": "deleted", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Job not found or could not be deleted")


# --- Monitoring Endpoints ---

@v1_router.get("/monitor/stats", response_model=MonitorStats)
async def get_monitor_stats_endpoint():
    try:
        stats = monitor_service.get_stats()
        return MonitorStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")

@v1_router.get("/monitor/logs/{user_id}", response_model=UserLogsResponse)
async def get_user_logs_endpoint(user_id: str):
    try:
        logs = monitor_service.get_user_logs(user_id)
        formatted_logs = [
            LogEntry(
                id=log.id,
                prompt=log.prompt,
                timestamp=log.timestamp,
                status=log.status,
                periodicity=log.periodicity,
                job_id=log.job_id
            ) for log in logs
        ]
        return UserLogsResponse(user_id=user_id, logs=formatted_logs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user logs: {str(e)}")

# Include the secured router into the app
app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
