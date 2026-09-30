from app.models.user import User

class PrivacyViolationError(Exception):
    """Exception raised when media is not opted-in for AI training."""
    ...

class PrivacyManager:
    """Manages user privacy and data retention operations."""
    
    def __init__(self, db_session=None):
        self.db_session = db_session


