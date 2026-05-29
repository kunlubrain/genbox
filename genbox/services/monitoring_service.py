import json
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta, date
from genbox.models.monitor_log import MonitorLog, SessionLocal
import logging

logger = logging.getLogger(__name__)

class MonitorService:
    def _generate_hash(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()

    def log_request(
        self, 
        user_id: str, 
        prompt: str, 
        status: str, 
        periodicity: str = "", 
        job_id: str = None,
        response_data: any = None
    ):
        db: Session = SessionLocal()
        try:
            resp_str = json.dumps(response_data) if response_data is not None else None
            
            log_entry = MonitorLog(
                user_id=user_id,
                prompt=prompt,
                prompt_hash=self._generate_hash(prompt),
                status=status,
                periodicity=periodicity,
                job_id=job_id,
                response_data=resp_str
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log request to DB: {str(e)}")
            db.rollback()
        finally:
            db.close()

    def get_user_logs(self, user_id: str, job_id: str | None = None, limit: int = 100) -> list[MonitorLog]:
        db: Session = SessionLocal()
        try:
            query = db.query(MonitorLog).filter(MonitorLog.user_id == user_id)
            if job_id:
                query = query.filter(MonitorLog.job_id == job_id)
            
            return query.order_by(desc(MonitorLog.timestamp)).limit(limit).all()
        finally:
            db.close()

    def get_cached_response(self, prompt: str, is_cron: bool = False) -> any:
        db: Session = SessionLocal()
        try:
            prompt_hash = self._generate_hash(prompt)
            time_limit = 18000 if is_cron else 3600
            cutoff = datetime.utcnow() - timedelta(seconds=time_limit)
            
            cached_log = db.query(MonitorLog).filter(
                MonitorLog.prompt_hash == prompt_hash,
                MonitorLog.status == "success",
                MonitorLog.timestamp >= cutoff
            ).order_by(desc(MonitorLog.timestamp)).first()
            
            if cached_log and cached_log.response_data:
                logger.info(f"Cache hit for prompt (is_cron={is_cron})")
                return json.loads(cached_log.response_data)
            
            return None
        finally:
            db.close()

    def get_stats(self):
        db: Session = SessionLocal()
        try:
            today = date.today()
            total = db.query(MonitorLog).count()
            success = db.query(MonitorLog).filter(MonitorLog.status == "success").count()
            failed = db.query(MonitorLog).filter(MonitorLog.status == "failed").count()
            
            dau = db.query(func.count(func.distinct(MonitorLog.user_id)))\
                .filter(func.date(MonitorLog.timestamp) == today)\
                .scalar()
            
            cron_today = db.query(MonitorLog)\
                .filter(func.date(MonitorLog.timestamp) == today)\
                .filter(MonitorLog.periodicity != "")\
                .count()

            return {
                "total_requests": total,
                "successful_requests": success,
                "failed_requests": failed,
                "dau": dau or 0,
                "cron_requests_today": cron_today
            }
        finally:
            db.close()

monitor_service = MonitorService()
