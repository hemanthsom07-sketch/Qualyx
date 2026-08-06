from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Simple liveness check. No database dependency on purpose,
    so this endpoint works even before the database is reachable."""
    return {"status": "ok"}
