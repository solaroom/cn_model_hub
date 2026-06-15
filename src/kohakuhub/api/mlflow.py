"""MLflow integration endpoints for cn_model_hub."""

import os
import time

import httpx
from fastapi import APIRouter

from kohakuhub.config import cfg

router = APIRouter()


def _tracking_uri() -> str:
    return (
        os.environ.get("MLFLOW_TRACKING_URI")
        or os.environ.get("KOHAKU_HUB_MLFLOW_TRACKING_URI")
        or cfg.app.mlflow_tracking_uri
    )


@router.get("/mlflow/status")
async def mlflow_status():
    """Return the configured MLflow tracking endpoint and basic reachability."""
    tracking_uri = _tracking_uri()
    if not tracking_uri:
        return {
            "enabled": False,
            "status": "disabled",
            "tracking_uri": "",
            "message": "MLflow tracking URI is not configured.",
        }

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{tracking_uri.rstrip('/')}/health")
        reachable = response.status_code < 500
        return {
            "enabled": True,
            "status": "ok" if reachable else "degraded",
            "tracking_uri": tracking_uri,
            "status_code": response.status_code,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }
    except Exception as exc:
        return {
            "enabled": True,
            "status": "down",
            "tracking_uri": tracking_uri,
            "message": str(exc),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }
