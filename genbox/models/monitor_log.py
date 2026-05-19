from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from genbox.core.config import settings

Base = declarative_base()

class MonitorLog(Base):
    __tablename__ = "monitor_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True)
    prompt = Column(Text)
    prompt_hash = Column(String(64), index=True) # Added for cache lookup
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(50))  # "success" or "failed"
    periodicity = Column(String(255), default="")  # Empty for non-cron, cron string for cron
    job_id = Column(String(255), nullable=True) # If it's a cron request
    response_data = Column(Text, nullable=True) # Added to store cached response
    
# Setup DB engine and session
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)
