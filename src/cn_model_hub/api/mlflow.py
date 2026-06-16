"""MLflow integration endpoints for cn_model_hub."""

import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cn_model_hub.auth.dependencies import get_current_user, get_optional_user
from cn_model_hub.auth.permissions import check_repo_read_permission, check_repo_write_permission
from cn_model_hub.config import cfg
from cn_model_hub.db import User
from cn_model_hub.db_operations import get_repository, update_repository
from cn_model_hub.api.repo.utils.hf import hf_repo_not_found

router = APIRouter()


def _tracking_uri() -> str:
    return (
        os.environ.get("MLFLOW_TRACKING_URI")
        or os.environ.get("CN_MODEL_HUB_MLFLOW_TRACKING_URI")
        or cfg.app.mlflow_tracking_uri
    )


def _repository_experiment_name(repo_type: str, namespace: str, name: str) -> str:
    return f"repo:{repo_type}:{namespace}/{name}"


async def _mlflow_request(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    tracking_uri = _tracking_uri()
    if not tracking_uri:
        raise HTTPException(503, detail="MLflow tracking URI is not configured")

    base = tracking_uri.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                f"{base}{path}",
                json=json_body,
                params=params,
            )
    except Exception as exc:
        raise HTTPException(502, detail=f"MLflow request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text or response.reason_phrase
        raise HTTPException(
            502, detail=f"MLflow returned {response.status_code}: {detail}"
        )

    if not response.content:
        return {}
    return response.json()


async def _resolve_or_create_experiment(
    *,
    repo_type: str,
    namespace: str,
    name: str,
    experiment_name: str | None,
) -> tuple[str, str]:
    resolved_name = experiment_name or _repository_experiment_name(
        repo_type, namespace, name
    )
    tracking_uri = _tracking_uri()
    if not tracking_uri:
        raise HTTPException(503, detail="MLflow tracking URI is not configured")

    base = tracking_uri.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{base}/api/2.0/mlflow/experiments/get-by-name",
                params={"experiment_name": resolved_name},
            )
    except Exception as exc:
        raise HTTPException(502, detail=f"MLflow request failed: {exc}") from exc

    if response.status_code == 200:
        experiment = response.json().get("experiment")
        if experiment:
            return resolved_name, str(experiment["experiment_id"])
    elif response.status_code not in (404,):
        detail = response.text or response.reason_phrase
        raise HTTPException(
            502, detail=f"MLflow returned {response.status_code}: {detail}"
        )

    create_result = await _mlflow_request(
        "POST",
        "/api/2.0/mlflow/experiments/create",
        json_body={
            "name": resolved_name,
            "tags": [
                {"key": "cn_model_hub.repo_id", "value": f"{namespace}/{name}"},
                {"key": "cn_model_hub.repo_type", "value": repo_type},
                {"key": "cn_model_hub.namespace", "value": namespace},
                {"key": "cn_model_hub.name", "value": name},
            ],
        },
        timeout=10.0,
    )
    experiment_id = create_result.get("experiment_id")
    if not experiment_id:
        raise HTTPException(502, detail="MLflow did not return experiment_id")
    return resolved_name, str(experiment_id)


def _serialize_repo_mlflow(repo) -> dict[str, Any]:
    last_synced_at = repo.mlflow_last_synced_at
    if last_synced_at and last_synced_at.tzinfo is None:
        last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)

    return {
        "enabled": repo.mlflow_enabled,
        "experiment_name": repo.mlflow_experiment_name,
        "experiment_id": repo.mlflow_experiment_id,
        "last_synced_at": (
            last_synced_at.astimezone(timezone.utc).isoformat() if last_synced_at else None
        ),
    }


class BindMlflowRequest(BaseModel):
    experiment_name: str | None = None


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


@router.get("/{repo_type}s/{namespace}/{name}/mlflow")
async def get_repo_mlflow_binding(
    repo_type: str,
    namespace: str,
    name: str,
    user: User | None = Depends(get_optional_user),
):
    repo = get_repository(repo_type, namespace, name)
    if not repo:
        return hf_repo_not_found(f"{namespace}/{name}", repo_type)

    check_repo_read_permission(repo, user)
    return _serialize_repo_mlflow(repo)


@router.post("/{repo_type}s/{namespace}/{name}/mlflow/bind")
async def bind_repo_mlflow(
    repo_type: str,
    namespace: str,
    name: str,
    payload: BindMlflowRequest | None = None,
    user: User = Depends(get_current_user),
):
    repo = get_repository(repo_type, namespace, name)
    if not repo:
        return hf_repo_not_found(f"{namespace}/{name}", repo_type)

    check_repo_write_permission(repo, user)
    experiment_name, experiment_id = await _resolve_or_create_experiment(
        repo_type=repo_type,
        namespace=namespace,
        name=name,
        experiment_name=payload.experiment_name if payload else None,
    )
    update_repository(
        repo,
        mlflow_enabled=True,
        mlflow_experiment_name=experiment_name,
        mlflow_experiment_id=experiment_id,
        mlflow_last_synced_at=datetime.now(timezone.utc),
    )
    repo = get_repository(repo_type, namespace, name)
    return {
        "success": True,
        "message": "Repository bound to MLflow experiment",
        "mlflow": _serialize_repo_mlflow(repo),
    }


@router.post("/{repo_type}s/{namespace}/{name}/mlflow/unbind")
async def unbind_repo_mlflow(
    repo_type: str,
    namespace: str,
    name: str,
    user: User = Depends(get_current_user),
):
    repo = get_repository(repo_type, namespace, name)
    if not repo:
        return hf_repo_not_found(f"{namespace}/{name}", repo_type)

    check_repo_write_permission(repo, user)
    update_repository(
        repo,
        mlflow_enabled=False,
        mlflow_experiment_name=None,
        mlflow_experiment_id=None,
        mlflow_last_synced_at=datetime.now(timezone.utc),
    )
    repo = get_repository(repo_type, namespace, name)
    return {
        "success": True,
        "message": "Repository unbound from MLflow experiment",
        "mlflow": _serialize_repo_mlflow(repo),
    }


@router.get("/{repo_type}s/{namespace}/{name}/mlflow/runs")
async def list_repo_mlflow_runs(
    repo_type: str,
    namespace: str,
    name: str,
    limit: int = 20,
    user: User | None = Depends(get_optional_user),
):
    repo = get_repository(repo_type, namespace, name)
    if not repo:
        return hf_repo_not_found(f"{namespace}/{name}", repo_type)

    check_repo_read_permission(repo, user)
    if not repo.mlflow_enabled or not repo.mlflow_experiment_id:
        return {
            "enabled": False,
            "experiment_id": repo.mlflow_experiment_id,
            "experiment_name": repo.mlflow_experiment_name,
            "runs": [],
        }

    payload = await _mlflow_request(
        "POST",
        "/api/2.0/mlflow/runs/search",
        json_body={
            "experiment_ids": [repo.mlflow_experiment_id],
            "max_results": max(1, min(limit, 100)),
            "order_by": ["attributes.start_time DESC"],
        },
        timeout=10.0,
    )
    runs = []
    for run in payload.get("runs", []):
        info = run.get("info", {})
        data = run.get("data", {})
        metrics = {
            item["key"]: item.get("value")
            for item in data.get("metrics", [])
            if "key" in item
        }
        params = {
            item["key"]: item.get("value")
            for item in data.get("params", [])
            if "key" in item
        }
        tags = {
            item["key"]: item.get("value")
            for item in data.get("tags", [])
            if "key" in item
        }
        runs.append(
            {
                "run_id": info.get("run_id"),
                "run_name": tags.get("mlflow.runName"),
                "status": info.get("status"),
                "artifact_uri": info.get("artifact_uri"),
                "start_time": info.get("start_time"),
                "end_time": info.get("end_time"),
                "metrics": metrics,
                "params": params,
                "tags": tags,
            }
        )

    return {
        "enabled": True,
        "experiment_id": repo.mlflow_experiment_id,
        "experiment_name": repo.mlflow_experiment_name,
        "runs": runs,
    }
