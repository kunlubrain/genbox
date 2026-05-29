import json
import csv
import io
import logging
import httpx
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from genbox.core.config import settings
from genbox.services.genai_service import genai_service
from genbox.models.schemas import ScheduleRequest
from genbox.services.monitoring_service import monitor_service

logger = logging.getLogger(__name__)

# Ensure results directory exists
RESULTS_DIR = "storage/results"
os.makedirs(RESULTS_DIR, exist_ok=True)

class SchedulerService:
    def __init__(self):
        job_stores = {
            'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
        }
        # Do not start here, it needs a running event loop
        self.scheduler = AsyncIOScheduler(jobstores=job_stores)

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started.")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down.")

    def _parse_schedule(self, schedule_days: str) -> dict[str, str]:
        """Convert custom schedule string (Mo, Tu or 1, 15) to APScheduler params."""
        days = [d.strip().lower() for d in schedule_days.split(',')]
        
        # Day of Week mapping
        dow_map = {
            'mo': 'mon', 'tu': 'tue', 'we': 'wed', 'th': 'thu', 
            'fr': 'fri', 'sa': 'sat', 'so': 'sun'
        }
        
        if 'dd' in days:
            return {'day': '*', 'day_of_week': '*'}
            
        # Check if they are numbers (day of month) or days of week
        if all(d.isdigit() for d in days):
            return {'day': ','.join(days), 'day_of_week': '*'}
        else:
            # Map Mo, Tu -> mon, tue
            dows = [dow_map.get(d, d) for d in days if d in dow_map]
            return {'day': '*', 'day_of_week': ','.join(dows)}

    async def schedule_job(self, request: ScheduleRequest) -> str:
        # Convert to cron params
        cron_params = self._parse_schedule(request.schedule_days)
        
        job_id = f"job_{request.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        self.scheduler.add_job(
            self.execute_and_callback,
            trigger='cron',
            hour=request.clock_hour,
            end_date=request.end_date,
            args=[request, job_id],
            id=job_id,
            replace_existing=True,
            **cron_params
        )
        
        logger.info(f"Scheduled job {job_id} for user {request.user_id}")
        return job_id

    def delete_job(self, job_id: str):
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Deleted job {job_id}")
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {str(e)}")
            raise

    async def execute_and_callback(self, request: ScheduleRequest, job_id: str):
        logger.info(f"Executing scheduled job {job_id}")
        
        try:
            # 1. Check Cache (18000s for cron)
            cached_data = monitor_service.get_cached_response(request.prompt, is_cron=True)
            if cached_data is not None:
                data = cached_data
                logger.info(f"Reusing cached response for cron job {job_id}")
            else:
                # Generate new content
                if request.response_type == "dict":
                    data = await genai_service.generate_dict(request.prompt, request.model_name, request.json_schema)
                elif request.response_type == "csv":
                    data = await genai_service.generate_csv(request.prompt, request.model_name)
                else:
                    data = await genai_service.generate_text(request.prompt, request.model_name)

            # 2. Local persistence (Logging to file)
            result = {
                "job_id": job_id,
                "user_id": request.user_id,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            file_path = f"{RESULTS_DIR}/{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(file_path, "w") as f:
                json.dump(result, f, indent=2)

            # 3. Callback with retry (only if callback_url is provided)
            if request.callback_url:
                await self._send_callback(request.callback_url, result)
            else:
                logger.info(f"No callback_url provided for job {job_id}, skipping webhook.")
            
            # 4. Monitor Log & Store Cache
            monitor_service.log_request(
                user_id=request.user_id,
                prompt=request.prompt,
                status="success",
                periodicity=request.schedule_days,
                job_id=job_id,
                response_data=data
            )
            
        except Exception as e:
            logger.error(f"Job execution failed for {job_id}: {str(e)}")
            monitor_service.log_request(
                user_id=request.user_id,
                prompt=request.prompt,
                status="failed",
                periodicity=request.schedule_days,
                job_id=job_id
            )

    # Retry logic: 2 attempts over an hour (approx every 30 mins)
    @retry(
        stop=stop_after_attempt(3), # 1 original + 2 retries
        wait=wait_exponential(multiplier=1800, min=1800, max=3600), # 30 mins to 1 hour
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def _send_callback(self, url: str, payload: dict):
        async with httpx.AsyncClient() as client:
            logger.info(f"Sending callback to {url}")
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()

scheduler_service = SchedulerService()
