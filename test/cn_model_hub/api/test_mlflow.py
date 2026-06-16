"""API tests for MLflow repository bindings."""

from __future__ import annotations

import httpx

from cn_model_hub.db_operations import get_repository


async def test_repo_info_includes_mlflow_binding(client):
    response = await client.get("/api/models/owner/demo-model")
    assert response.status_code == 200
    payload = response.json()
    assert "mlflow" in payload
    assert payload["mlflow"]["enabled"] is False
    assert payload["mlflow"]["experiment_name"] is None


async def test_bind_repository_to_mlflow_experiment(owner_client, monkeypatch):
    recorded = []

    class FakeResponse:
        def __init__(self, status_code, payload=None, text=""):
            self.status_code = status_code
            self._payload = payload or {}
            self.text = text
            self.reason_phrase = text or ""

        def json(self):
            return self._payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            recorded.append(("GET", url, {"params": params}))
            return FakeResponse(404, {"error_code": "RESOURCE_DOES_NOT_EXIST"})

    async def fake_mlflow_request(method, path, **kwargs):
        recorded.append((method, path, kwargs))
        if path.endswith("/experiments/create"):
            return {"experiment_id": "exp-123"}
        raise AssertionError(f"unexpected path: {path}")

    import cn_model_hub.api.mlflow as mlflow_api

    monkeypatch.setattr(mlflow_api.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(mlflow_api, "_mlflow_request", fake_mlflow_request)

    response = await owner_client.post(
        "/api/models/owner/demo-model/mlflow/bind", json={}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mlflow"]["enabled"] is True
    assert payload["mlflow"]["experiment_id"] == "exp-123"
    assert payload["mlflow"]["experiment_name"] == "repo:model:owner/demo-model"

    repo = get_repository("model", "owner", "demo-model")
    assert repo is not None
    assert repo.mlflow_enabled is True
    assert repo.mlflow_experiment_id == "exp-123"

    assert recorded[0][0] == "GET"
    assert recorded[0][1].endswith("/api/2.0/mlflow/experiments/get-by-name")
    assert recorded[1][1] == "/api/2.0/mlflow/experiments/create"


async def test_bind_repository_reuses_existing_mlflow_experiment(owner_client, monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload
            self.text = ""
            self.reason_phrase = ""

        def json(self):
            return self._payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            return FakeResponse(
                {"experiment": {"experiment_id": "exp-existing"}}
            )

    async def fake_mlflow_request(method, path, **kwargs):
        raise AssertionError("create should not be called when experiment exists")

    import cn_model_hub.api.mlflow as mlflow_api

    monkeypatch.setattr(mlflow_api.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(mlflow_api, "_mlflow_request", fake_mlflow_request)

    response = await owner_client.post(
        "/api/models/owner/demo-model/mlflow/bind", json={}
    )
    assert response.status_code == 200
    assert response.json()["mlflow"]["experiment_id"] == "exp-existing"


async def test_list_repository_mlflow_runs(owner_client, monkeypatch):
    repo = get_repository("model", "owner", "demo-model")
    assert repo is not None
    repo.mlflow_enabled = True
    repo.mlflow_experiment_name = "repo:model:owner/demo-model"
    repo.mlflow_experiment_id = "exp-001"
    repo.save()

    async def fake_mlflow_request(method, path, **kwargs):
        assert method == "POST"
        assert path == "/api/2.0/mlflow/runs/search"
        return {
            "runs": [
                {
                    "info": {
                        "run_id": "run-1",
                        "status": "FINISHED",
                        "artifact_uri": "mlflow-artifacts:/run-1",
                        "start_time": 1710000000000,
                        "end_time": 1710000005000,
                    },
                    "data": {
                        "metrics": [{"key": "accuracy", "value": 0.98}],
                        "params": [{"key": "batch_size", "value": "8"}],
                        "tags": [{"key": "mlflow.runName", "value": "eval-main"}],
                    },
                }
            ]
        }

    import cn_model_hub.api.mlflow as mlflow_api

    monkeypatch.setattr(mlflow_api, "_mlflow_request", fake_mlflow_request)

    response = await owner_client.get("/api/models/owner/demo-model/mlflow/runs")
    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["experiment_id"] == "exp-001"
    assert payload["runs"][0]["run_id"] == "run-1"
    assert payload["runs"][0]["run_name"] == "eval-main"
    assert payload["runs"][0]["metrics"]["accuracy"] == 0.98
    assert payload["runs"][0]["params"]["batch_size"] == "8"


async def test_non_owner_cannot_bind_mlflow(member_client):
    response = await member_client.post(
        "/api/models/owner/demo-model/mlflow/bind", json={}
    )
    assert response.status_code == 403


async def test_private_repo_mlflow_read_requires_access(app, owner_client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as anonymous_client:
        response = await anonymous_client.get(
            "/api/datasets/acme-labs/private-dataset/mlflow"
        )
        assert response.status_code == 404
        assert response.headers["x-error-code"] == "RepoNotFound"

    authed = await owner_client.get("/api/datasets/acme-labs/private-dataset/mlflow")
    assert authed.status_code == 200
