from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

if "torch" not in sys.modules:
    torch_stub = ModuleType("torch")
    torch_stub.cuda = SimpleNamespace(
        is_available=lambda: False,
        get_device_name=lambda index: None,
    )
    sys.modules["torch"] = torch_stub

from scripts import remote_runtime_agent as agent


class FakeProcess:
    def __init__(self, pid: int):
        self.pid = pid
        self.returncode = None
        self.stdout = None

    def terminate(self) -> None:
        self.returncode = 0

    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode or 0


@pytest.fixture(autouse=True)
def reset_runtime_state():
    agent.runtimes.clear()
    agent.runtime_locks.clear()
    agent.evaluations.clear()
    yield
    agent.runtimes.clear()
    agent.runtime_locks.clear()
    agent.evaluations.clear()


@pytest.mark.asyncio
async def test_different_models_can_run_at_the_same_time(tmp_path, monkeypatch):
    async def fake_ensure_venv(state, root):
        return Path("/fake/python")

    async def fake_create_subprocess(*args, **kwargs):
        return FakeProcess(pid=1000 + len(agent.active_runtime_keys()))

    async def fake_wait_for_http(state, timeout=60.0):
        await asyncio.sleep(0)
        state["status"] = "running"
        state["message"] = "Runtime is running."

    monkeypatch.setattr(
        agent,
        "runtime_dir",
        lambda runtime_key, root=None: tmp_path / runtime_key,
    )
    monkeypatch.setattr(agent, "ensure_venv", fake_ensure_venv)
    monkeypatch.setattr(agent.asyncio, "create_subprocess_exec", fake_create_subprocess)
    monkeypatch.setattr(agent, "wait_for_http", fake_wait_for_http)

    requests = []
    for runtime_key in ("model-alice-one", "model-alice-two"):
        root = tmp_path / runtime_key
        current = root / "current"
        current.mkdir(parents=True)
        (current / "app.py").write_text("pass", encoding="utf-8")
        (root / ".commit").write_text("commit-1", encoding="utf-8")
        requests.append(
            agent.RuntimeStartRequest(
                runtime_key=runtime_key,
                repo_type="model",
                repo_id=runtime_key,
                commit_id="commit-1",
                install_requirements=False,
            )
        )

    statuses = await asyncio.gather(*(agent.runtime_start(req) for req in requests))

    assert [status["status"] for status in statuses] == ["running", "running"]
    assert agent.active_runtime_keys() == ["model-alice-one", "model-alice-two"]
    assert len({status["port"] for status in statuses}) == 2

    stopped = await agent.stop_runtime_process("model-alice-one", "test")

    assert stopped["status"] == "stopped"
    assert agent.active_runtime_keys() == ["model-alice-two"]


def test_health_reports_all_active_models(monkeypatch):
    agent.runtimes.update(
        {
            "model-b": {"process": FakeProcess(2), "status": "running"},
            "model-a": {"process": FakeProcess(1), "status": "running"},
        }
    )
    monkeypatch.setattr(agent.torch.cuda, "is_available", lambda: False)

    result = agent.health()

    assert result["active_runtime_keys"] == ["model-a", "model-b"]
    assert result["active_runtime_count"] == 2


def test_evaluation_script_requires_cuda_and_validates_checkpoint():
    assert 'if not torch.cuda.is_available()' in agent.EVALUATION_SCRIPT
    assert "torch_dtype=torch.bfloat16" in agent.EVALUATION_SCRIPT
    assert "output_embeddings.weight.abs().max().item() == 0" in agent.EVALUATION_SCRIPT


def test_public_evaluation_status_reports_missing_and_completed():
    assert agent.public_evaluation_status("missing")["status"] == "not_found"
    agent.evaluations["eval-1"] = {
        "status": "completed",
        "runtime_key": "model-alice-one",
        "result": {"total": 20, "correct": 10, "accuracy": 0.5},
        "logs": [],
    }

    status = agent.public_evaluation_status("eval-1")

    assert status["status"] == "completed"
    assert status["result"]["accuracy"] == 0.5


def test_runtime_status_reports_installed_commit(tmp_path, monkeypatch):
    root = tmp_path / "model-alice-one"
    root.mkdir()
    (root / ".commit").write_text("installed-commit", encoding="utf-8")
    monkeypatch.setattr(agent, "runtime_dir", lambda runtime_key: root)

    status = agent.public_runtime_status("model-alice-one")

    assert status["installed_commit_id"] == "installed-commit"


def test_prepare_runtime_source_removes_redundant_upload(tmp_path):
    current = tmp_path / "current"
    incoming = tmp_path / "incoming"
    current.mkdir()
    incoming.mkdir()
    (tmp_path / ".commit").write_text("commit-1", encoding="utf-8")
    uploaded = incoming / "source.tar.gz"
    uploaded.write_bytes(b"redundant")

    result = agent.prepare_runtime_source(tmp_path, "commit-1")

    assert result == current
    assert uploaded.exists() is False
