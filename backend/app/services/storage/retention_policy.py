import datetime
from sqlalchemy.orm import Session
from app.services.storage.s3_storage import S3StorageService

class RetentionPolicyService:
    """
    Option 3: Auto-Delete (Retention Policy)
    Runs as a daily cron job to delete raw video files older than 24 hours for free users.
    """
    def __init__(self, db: Session):
        self.db = db
        self.s3_service = S3StorageService()
        self.FREE_TIER_RETENTION_HOURS = 24

