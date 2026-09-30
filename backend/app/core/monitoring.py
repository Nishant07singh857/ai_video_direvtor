import time
from typing import Callable, Any
from functools import wraps

class MetricsMock:
    def __init__(self) -> None:
        self.upload_times: list[float] = []
        self.render_jobs: int = 0

metrics = MetricsMock()

def track_upload_time(duration: float) -> None:
    """Mock tracking of upload time."""
    metrics.upload_times.append(duration)


