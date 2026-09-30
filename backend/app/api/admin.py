from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["admin"])

@router.get("/stats")
async def get_system_stats():
    """
    Returns basic platform stats (mocked).
    """
    return {
        "user_count": 1250,
        "active_jobs": 34,
        "status": "healthy"
    }
