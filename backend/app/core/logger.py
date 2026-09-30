import logging
import json
from typing import Any, Optional

class StructuredLogger:
    def __init__(self, name: str) -> None:
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            import sys
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except Exception:
                pass
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _format_log(self, level: str, message: str, request_id: Optional[str] = None, 
                    job_id: Optional[str] = None, model_id: Optional[str] = None, **kwargs: Any) -> str:
        log_record: dict[str, Any] = {
            "level": level,
            "message": message,
        }
        if request_id is not None:
            log_record["request_id"] = request_id
        if job_id is not None:
            log_record["job_id"] = job_id
        if model_id is not None:
            log_record["model_id"] = model_id
        
        log_record.update(kwargs)
        return json.dumps(log_record, default=str)

    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(self._format_log("INFO", message, **kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        self.logger.error(self._format_log("ERROR", message, **kwargs))


    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(self._format_log("DEBUG", message, **kwargs))
