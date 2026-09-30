import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class DatabaseBackupManager:
    def __init__(self, backup_dir: str = "/backups"):
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

