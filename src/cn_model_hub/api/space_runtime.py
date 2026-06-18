"""Minimal repository runtime support.

This intentionally implements a small local runtime instead of the full
HuggingFace Spaces platform. A model or Space repository can be materialized
from LakeFS, started as a Python process, and exposed through an HTTP proxy
for the web UI.
"""

import asyncio
import hashlib
import os
import re
import tarfile
import tempfile
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
import shutil
import socket
import sys
from urllib.parse import quote, urljoin

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from cn_model_hub.auth.dependencies import get_current_user, get_optional_user
from cn_model_hub.auth.permissions import (
    RepoReadDeniedError,
    check_repo_read_permission,
    check_repo_write_permission,
)
from cn_model_hub.config import cfg
from cn_model_hub.db import Repository, User
from cn_model_hub.db_operations import get_repository
from cn_model_hub.logger import get_logger
from cn_model_hub.utils.lakefs import get_lakefs_client, lakefs_repo_name, resolve_revision

logger = get_logger("SPACE_RUNTIME")
router = APIRouter()

RUNTIME_LOG_LINES = 5000
SUPPORTED_RUNTIME_REPO_TYPES = {"model", "space"}
BUILTIN_QWEN_LOCAL_REQUIREMENTS = [
    "accelerate>=0.30",
    "gradio>=4.44,<6",
    "huggingface_hub<1.0",
    "safetensors>=0.4",
    "sentencepiece>=0.2",
    "socksio>=1.0",
    "transformers>=4.43",
]
BUILTIN_QWEN_LOCAL_TORCH_REQUIREMENTS = ["torch>=2.1"]
PYTORCH_CPU_INDEX_URL = "https://download.pytorch.org/whl/cpu"
BUILTIN_QWEN_LOCAL_APP = r'''"""Local Qwen2.5 chat demo for cn_model_hub model repositories."""

from __future__ import annotations

import os
from pathlib import Path

import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_PATH = Path(os.getenv("LOCAL_MODEL_PATH", ".")).resolve()
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "256"))
SYSTEM_PROMPT = os.getenv(
    "QWEN_SYSTEM_PROMPT",
    "你是运行在中文开源AI模型社区里的本地千问助手，请用简洁、准确的中文回答。",
)

_tokenizer = None
_model = None
_device = "cpu"


def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps and mps.is_available():
        return "mps"
    return "cpu"


def _load_model():
    global _tokenizer, _model, _device
    if _model is not None and _tokenizer is not None:
        return _tokenizer, _model, _device

    _device = _pick_device()
    torch_dtype = torch.float16 if _device == "cuda" else torch.float32
    _tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH,
        trust_remote_code=True,
        local_files_only=True,
    )
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch_dtype,
        trust_remote_code=True,
        local_files_only=True,
    )
    _model.to(_device)
    _model.eval()
    return _tokenizer, _model, _device


def _messages(message: str, history) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history or []:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
            continue
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            if item[0]:
                messages.append({"role": "user", "content": item[0]})
            if item[1]:
                messages.append({"role": "assistant", "content": item[1]})
    messages.append({"role": "user", "content": message})
    return messages


def chat(message: str, history):
    try:
        tokenizer, model, device = _load_model()
        messages = _messages(message, history)
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer([text], return_tensors="pt").to(device)
        inputs.pop("token_type_ids", None)
        with torch.no_grad():
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=True,
                temperature=float(os.getenv("TEMPERATURE", "0.7")),
                top_p=float(os.getenv("TOP_P", "0.9")),
                pad_token_id=tokenizer.eos_token_id,
            )
        output_ids = generated_ids[0][inputs.input_ids.shape[-1]:]
        answer = tokenizer.decode(output_ids, skip_special_tokens=True)
        return answer.strip() or "模型没有生成内容。"
    except Exception as exc:
        return (
            "本地模型启动或推理失败。\n\n"
            f"模型目录：{MODEL_PATH}\n\n"
            f"错误：{exc}"
        )


demo = gr.ChatInterface(
    fn=chat,
    title="Qwen2.5-0.5B 本地模型 Demo",
    description="直接加载当前模型仓库中的本地权重文件进行推理。",
    examples=["用一句话介绍你自己", "给我一个中文开源模型社区的项目介绍"],
    type="messages",
)


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", "7860")))
    server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    root_path = os.getenv("GRADIO_ROOT_PATH") or None
    demo.launch(server_name=server_name, server_port=port, root_path=root_path)
'''
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}


class RuntimeStartPayload(BaseModel):
    revision: str = "main"
    install_requirements: bool | None = None


@dataclass
class RuntimeState:
    repo_type: str
    namespace: str
    name: str
    revision: str
    commit_id: str
    port: int
    workdir: Path
    process: asyncio.subprocess.Process | None = None
    status: str = "starting"
    message: str = ""
    logs: deque[str] = field(default_factory=lambda: deque(maxlen=RUNTIME_LOG_LINES))

    @property
    def proxy_url(self) -> str:
        return (
            f"/api/{quote(self.repo_type + 's', safe='')}/"
            f"{quote(self.namespace, safe='')}/"
            f"{quote(self.name, safe='')}/runtime/proxy/"
        )

    @property
    def app_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def append_log(self, line: str) -> None:
        self.logs.append(line.rstrip())


_runtimes: dict[str, RuntimeState] = {}
_locks: dict[str, asyncio.Lock] = {}
_remote_statuses: dict[str, dict] = {}


def _runtime_key(repo_type: str, namespace: str, name: str) -> str:
    return f"{repo_type}:{namespace}/{name}"


def _remote_runtime_key(repo_type: str, namespace: str, name: str) -> str:
    raw = f"{repo_type}-{namespace}-{name}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-")[:160]


def _normalize_repo_type(repo_type: str) -> str:
    singular = repo_type[:-1] if repo_type.endswith("s") else repo_type
    if singular not in SUPPORTED_RUNTIME_REPO_TYPES:
        raise HTTPException(
            400,
            detail={"error": "Runtime only supports model and space repositories."},
        )
    return singular


def _runtime_root() -> Path:
    root = Path(cfg.app.space_runtime_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _remote_enabled() -> bool:
    return cfg.app.space_runtime_backend.lower() == "remote"


def _remote_headers() -> dict[str, str]:
    headers = {}
    if cfg.app.space_runtime_remote_api_key:
        headers["Authorization"] = f"Bearer {cfg.app.space_runtime_remote_api_key}"
    return headers


def _remote_agent_url(path: str) -> str:
    base_url = cfg.app.space_runtime_remote_base_url.rstrip("/")
    if not base_url:
        raise HTTPException(
            500,
            detail={"error": "Remote runtime backend is enabled but base URL is empty."},
        )
    return f"{base_url}{path}"


def _safe_child_path(root: Path, path: str) -> Path | None:
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _runtime_venv_dir(state: RuntimeState) -> Path:
    return state.workdir / ".cn_model_hub_runtime_venv"


def _runtime_python(state: RuntimeState) -> Path:
    venv = _runtime_venv_dir(state)
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


async def _ensure_runtime_venv(state: RuntimeState) -> Path:
    python = _runtime_python(state)
    if python.exists():
        return python

    venv = _runtime_venv_dir(state)
    uv = shutil.which("uv")
    if uv:
        proc = await asyncio.create_subprocess_exec(
            uv,
            "venv",
            "--seed",
            str(venv),
            cwd=str(state.workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "venv",
            "--upgrade-deps",
            str(venv),
            cwd=str(state.workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

    if proc.stdout:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            state.append_log(line.decode(errors="replace"))
    code = await proc.wait()
    if code != 0:
        raise RuntimeError(f"runtime venv creation failed with code {code}")
    return python


def _repo_or_404(repo_type: str, namespace: str, name: str) -> Repository:
    repo = get_repository(repo_type, namespace, name)
    if not repo:
        raise HTTPException(404, detail={"error": f"{repo_type} repository not found"})
    return repo


def _public_status(state: RuntimeState | None) -> dict:
    if not state:
        return {
            "status": "stopped",
            "message": "Demo 尚未启动。",
            "proxy_url": "",
            "logs": [],
        }

    running = state.process is not None and state.process.returncode is None
    if state.status == "running" and not running:
        state.status = "stopped"
        state.message = f"Runtime process exited with code {state.process.returncode}."

    return {
        "status": state.status,
        "message": state.message,
        "revision": state.revision,
        "commit_id": state.commit_id,
        "proxy_url": state.proxy_url if state.status == "running" else "",
        "logs": list(state.logs),
        "log_limit": RUNTIME_LOG_LINES,
    }


def _public_remote_status(repo: Repository, data: dict | None) -> dict:
    if not data:
        return {
            "status": "stopped",
            "message": "Demo 尚未启动。",
            "proxy_url": "",
            "logs": [],
        }
    status = data.get("status") or "stopped"
    active_runtime_keys = data.get("active_runtime_keys") or []
    return {
        "status": status,
        "message": data.get("message") or "",
        "revision": data.get("revision") or "main",
        "commit_id": data.get("commit_id") or "",
        "proxy_url": (
            f"/api/{quote(repo.repo_type + 's', safe='')}/"
            f"{quote(repo.namespace, safe='')}/"
            f"{quote(repo.name, safe='')}/runtime/proxy/"
            if status in {"running", "starting"}
            else ""
        ),
        "logs": data.get("logs") or [],
        "log_limit": data.get("log_limit") or RUNTIME_LOG_LINES,
        "active_runtime_keys": active_runtime_keys,
        "active_runtime_count": len(active_runtime_keys),
        "gpu": data.get("gpu"),
        "cuda_available": data.get("cuda_available"),
    }


def _demo_label(repo_type: str) -> str:
    return "模型 Demo" if repo_type == "model" else "Space Demo"


def _ui_repo_path(repo: Repository, *, tab: str | None = None) -> str:
    path = (
        f"/{quote(repo.repo_type + 's', safe='')}/"
        f"{quote(repo.namespace, safe='')}/"
        f"{quote(repo.name, safe='')}"
    )
    return f"{path}?tab={quote(tab, safe='')}" if tab else path


def _repo_last_modified(repo: Repository) -> str | None:
    latest = None
    try:
        from cn_model_hub.db import File

        latest = (
            File.select(File.updated_at)
            .where((File.repository == repo) & (File.is_deleted == False))  # noqa: E712
            .order_by(File.updated_at.desc())
            .first()
        )
    except Exception:
        latest = None
    dt = getattr(latest, "updated_at", None) or repo.created_at
    return dt.isoformat() if dt else None


def _serialize_demo(repo: Repository, state: RuntimeState | None) -> dict:
    if _remote_enabled():
        status = _public_remote_status(
            repo, _remote_statuses.get(_runtime_key(repo.repo_type, repo.namespace, repo.name))
        )
    else:
        status = _public_status(state)
    return {
        "id": _runtime_key(repo.repo_type, repo.namespace, repo.name),
        "repo_type": repo.repo_type,
        "namespace": repo.namespace,
        "name": repo.name,
        "full_id": repo.full_id,
        "demo_label": _demo_label(repo.repo_type),
        "detail_url": _ui_repo_path(repo, tab="runtime"),
        "created_at": repo.created_at.isoformat() if repo.created_at else None,
        "last_modified": _repo_last_modified(repo),
        "downloads": repo.downloads,
        "likes": repo.likes_count,
        **status,
    }


async def _list_all_objects(lakefs_repo: str, ref: str) -> list[dict]:
    client = get_lakefs_client()
    objects: list[dict] = []
    after = ""
    while True:
        page = await client.list_objects(
            repository=lakefs_repo,
            ref=ref,
            prefix="",
            delimiter="",
            amount=1000,
            after=after,
        )
        objects.extend(
            item for item in page.get("results", []) if item.get("path_type") == "object"
        )
        pagination = page.get("pagination", {})
        if not pagination.get("has_more"):
            break
        after = pagination.get("next_offset", "")
    return objects


async def _materialize_repo(repo: Repository, revision: str) -> tuple[Path, str]:
    repo_id = f"{repo.namespace}/{repo.name}"
    lakefs_repo = lakefs_repo_name(repo.repo_type, repo_id)
    client = get_lakefs_client()
    commit_id, _ = await resolve_revision(client, lakefs_repo, revision)
    digest = hashlib.sha256(
        f"{repo.repo_type}:{repo_id}:{commit_id}".encode()
    ).hexdigest()[:16]
    workdir = _runtime_root() / f"{repo.repo_type}-{repo.namespace}-{repo.name}-{digest}"

    if workdir.exists() and (workdir / ".cn_model_hub_synced").exists():
        return workdir, commit_id

    tmpdir = workdir.with_suffix(".tmp")
    if tmpdir.exists():
        shutil.rmtree(tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)

    for obj in await _list_all_objects(lakefs_repo, commit_id):
        path = obj.get("path") or ""
        target = _safe_child_path(tmpdir, path)
        if target is None:
            logger.warning(f"Skipping unsafe runtime path: {path}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        await client.download_object(
            repository=lakefs_repo,
            ref=commit_id,
            path=path,
            target=target,
        )

    (tmpdir / ".cn_model_hub_synced").write_text(commit_id, encoding="utf-8")
    if workdir.exists():
        shutil.rmtree(workdir)
    tmpdir.rename(workdir)
    return workdir, commit_id


def _create_runtime_tar(workdir: Path) -> Path:
    package_dir = _runtime_root() / "_packages"
    package_dir.mkdir(parents=True, exist_ok=True)
    fd, package_name = tempfile.mkstemp(
        prefix=f"{workdir.name}-", suffix=".tar.gz", dir=str(package_dir)
    )
    os.close(fd)
    package_path = Path(package_name)
    # Model weights are already compressed and can be tens of gigabytes.
    # Gzip adds minutes of CPU time without materially reducing the upload.
    with tarfile.open(package_path, "w") as archive:
        for child in workdir.iterdir():
            if child.name == ".cn_model_hub_runtime_venv":
                continue
            archive.add(child, arcname=child.name)
    return package_path


async def _run_upload_command(command: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output = await proc.communicate()
    if proc.returncode != 0:
        text = (output[0] or b"").decode(errors="replace")
        raise RuntimeError(f"{command[0]} failed with code {proc.returncode}: {text}")


async def _stream_file_to_remote(command: list[str], package_path: Path) -> None:
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    assert proc.stdin is not None
    with package_path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            proc.stdin.write(chunk)
            await proc.stdin.drain()
    proc.stdin.close()
    output = await proc.communicate()
    if proc.returncode != 0:
        text = (output[0] or b"").decode(errors="replace")
        raise RuntimeError(f"{command[0]} upload failed with code {proc.returncode}: {text}")


async def _upload_runtime_package(remote_key: str, package_path: Path) -> None:
    if cfg.app.space_runtime_remote_upload_method.lower() != "ssh":
        raise RuntimeError("Only ssh remote runtime upload is supported.")
    ssh_alias = cfg.app.space_runtime_remote_ssh_alias
    remote_dir = f"{cfg.app.space_runtime_remote_root.rstrip('/')}/{remote_key}/incoming"
    await _run_upload_command(["ssh", ssh_alias, f"mkdir -p {remote_dir}"])
    await _stream_file_to_remote(
        ["ssh", ssh_alias, f"cat > {remote_dir}/source.tar.gz"],
        package_path,
    )


async def _remote_agent_get_status(remote_key: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            _remote_agent_url(f"/api/runtime/status/{quote(remote_key, safe='')}"),
            headers=_remote_headers(),
        )
    if response.status_code == 404:
        return {"status": "stopped", "runtime_key": remote_key}
    if response.status_code >= 400:
        raise RuntimeError(response.text)
    return response.json()


async def _remote_agent_stop(remote_key: str, reason: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            _remote_agent_url("/api/runtime/stop"),
            headers=_remote_headers(),
            json={"runtime_key": remote_key, "reason": reason},
        )
    if response.status_code >= 400:
        raise RuntimeError(response.text)
    return response.json()


async def _remote_agent_start(
    repo: Repository,
    remote_key: str,
    revision: str,
    commit_id: str,
    install_requirements: bool,
    using_builtin_model_app: bool,
) -> dict:
    payload = {
        "runtime_key": remote_key,
        "repo_type": repo.repo_type,
        "repo_id": f"{repo.namespace}/{repo.name}",
        "revision": revision,
        "commit_id": commit_id,
        "remote_root": cfg.app.space_runtime_remote_root,
        "app_entry": "app.py",
        "using_builtin_model_app": using_builtin_model_app,
        "install_requirements": install_requirements,
        "env": {
            "CN_MODEL_HUB_REPO_TYPE": repo.repo_type,
            "CN_MODEL_HUB_REPO_ID": f"{repo.namespace}/{repo.name}",
            "CN_MODEL_HUB_SPACE_ID": f"{repo.namespace}/{repo.name}",
            "CN_MODEL_HUB_SPACE_REVISION": revision,
            "CN_MODEL_HUB_SPACE_COMMIT": commit_id,
            "CN_MODEL_HUB_REPO_REVISION": revision,
            "CN_MODEL_HUB_REPO_COMMIT": commit_id,
            "MAX_NEW_TOKENS": "256",
            "MLFLOW_TRACKING_URI": cfg.app.mlflow_tracking_uri,
            "MLFLOW_EXPERIMENT_NAME": repo.mlflow_experiment_name or "",
            "MLFLOW_EXPERIMENT_ID": repo.mlflow_experiment_id or "",
        },
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            _remote_agent_url("/api/runtime/start"),
            headers=_remote_headers(),
            json=payload,
        )
    if response.status_code >= 400:
        raise RuntimeError(response.text)
    return response.json()


async def _start_remote_runtime(
    repo: Repository,
    revision: str,
    install_requirements: bool,
) -> dict:
    key = _runtime_key(repo.repo_type, repo.namespace, repo.name)
    remote_key = _remote_runtime_key(repo.repo_type, repo.namespace, repo.name)
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        workdir, commit_id = await _materialize_repo(repo, revision)
        using_builtin_model_app = repo.repo_type == "model" and not (workdir / "app.py").exists()
        remote_status = await _remote_agent_get_status(remote_key)
        if (
            remote_status.get("status") == "running"
            and remote_status.get("commit_id") == commit_id
        ):
            _remote_statuses[key] = remote_status
            return remote_status

        if remote_status.get("commit_id") != commit_id:
            try:
                await _remote_agent_stop(remote_key, "repository updated")
            except Exception as exc:
                logger.warning(f"Failed to stop stale remote runtime {remote_key}: {exc}")
            package_path = _create_runtime_tar(workdir)
            try:
                await _upload_runtime_package(remote_key, package_path)
            finally:
                try:
                    package_path.unlink(missing_ok=True)
                except Exception:
                    pass

        started = await _remote_agent_start(
            repo,
            remote_key,
            revision,
            commit_id,
            install_requirements,
            using_builtin_model_app,
        )
        _remote_statuses[key] = started
        return started


async def _read_process_output(state: RuntimeState) -> None:
    if state.process is None or state.process.stdout is None:
        return
    while True:
        line = await state.process.stdout.readline()
        if not line:
            break
        state.append_log(line.decode(errors="replace"))


async def _wait_for_http(state: RuntimeState, timeout: float = 30.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    async with httpx.AsyncClient(timeout=1.0) as client:
        while asyncio.get_running_loop().time() < deadline:
            if state.process and state.process.returncode is not None:
                state.status = "error"
                state.message = f"Runtime process exited with code {state.process.returncode}."
                return
            try:
                response = await client.get(state.app_url)
                if response.status_code < 500:
                    state.status = "running"
                    state.message = "Runtime is running."
                    return
            except Exception:
                await asyncio.sleep(0.5)
    state.status = "starting"
    state.message = "Runtime process started, but the HTTP endpoint is still warming up."


async def _install_requirements(state: RuntimeState) -> None:
    requirements = state.workdir / "requirements.txt"
    if not requirements.exists():
        return

    marker = state.workdir / ".requirements.sha256"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    if marker.exists() and marker.read_text(encoding="utf-8") == digest:
        return

    state.append_log("Installing requirements.txt ...")
    code = await _run_package_install(
        state,
        ["-r", str(requirements)],
    )
    if code != 0:
        raise RuntimeError(f"requirements.txt install failed with code {code}")
    marker.write_text(digest, encoding="utf-8")


async def _run_package_install(state: RuntimeState, args: list[str]) -> int:
    python = await _ensure_runtime_venv(state)
    uv = shutil.which("uv")
    if uv:
        code = await _run_logged_process(
            state,
            [
                uv,
                "pip",
                "install",
                "--python",
                str(python),
                *args,
            ],
        )
        if code == 0:
            return 0
        state.append_log(
            f"uv package install failed with code {code}; retrying with pip ..."
        )

    return await _run_logged_process(
        state,
        [str(python), "-m", "pip", "install", *args],
    )


async def _run_logged_process(state: RuntimeState, command: list[str]) -> int:
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(state.workdir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    if proc.stdout:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            state.append_log(line.decode(errors="replace"))
    return await proc.wait()


async def _install_builtin_model_requirements(state: RuntimeState) -> None:
    digest = hashlib.sha256(
        "\n".join(
            [
                os.getenv("CN_MODEL_HUB_PYTORCH_CPU_INDEX_URL", PYTORCH_CPU_INDEX_URL),
                *BUILTIN_QWEN_LOCAL_TORCH_REQUIREMENTS,
                *BUILTIN_QWEN_LOCAL_REQUIREMENTS,
            ]
        ).encode()
    ).hexdigest()
    marker = state.workdir / ".builtin-qwen-local-requirements.sha256"
    if marker.exists() and marker.read_text(encoding="utf-8") == digest:
        return

    state.append_log("Installing built-in local Qwen runtime requirements ...")
    state.append_log("Installing CPU-only PyTorch runtime ...")
    torch_code = await _run_package_install(
        state,
        [
            "--extra-index-url",
            os.getenv("CN_MODEL_HUB_PYTORCH_CPU_INDEX_URL", PYTORCH_CPU_INDEX_URL),
            *BUILTIN_QWEN_LOCAL_TORCH_REQUIREMENTS,
        ],
    )
    if torch_code != 0:
        raise RuntimeError(
            f"built-in local model torch install failed with code {torch_code}"
        )

    code = await _run_package_install(state, BUILTIN_QWEN_LOCAL_REQUIREMENTS)
    if code != 0:
        raise RuntimeError(
            f"built-in local model requirements install failed with code {code}"
        )
    marker.write_text(digest, encoding="utf-8")


def _resolve_app_file(state: RuntimeState) -> tuple[Path, bool]:
    custom_app = state.workdir / "app.py"
    if custom_app.exists():
        return custom_app, False
    if state.repo_type == "model":
        builtin_app = state.workdir / ".cn_model_hub_qwen_local_app.py"
        builtin_app.write_text(BUILTIN_QWEN_LOCAL_APP, encoding="utf-8")
        return builtin_app, True
    raise HTTPException(
        400,
        detail={"error": "Space requires an app.py file for the simplified runtime."},
    )


async def _start_runtime(
    repo: Repository,
    revision: str,
    install_requirements: bool,
) -> RuntimeState:
    key = _runtime_key(repo.repo_type, repo.namespace, repo.name)
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        current = _runtimes.get(key)
        if current and current.process and current.process.returncode is None:
            return current

        workdir, commit_id = await _materialize_repo(repo, revision)

        state = RuntimeState(
            repo_type=repo.repo_type,
            namespace=repo.namespace,
            name=repo.name,
            revision=revision,
            commit_id=commit_id,
            port=_free_port(),
            workdir=workdir,
        )
        _runtimes[key] = state

        try:
            app_file, using_builtin_model_app = _resolve_app_file(state)
            runtime_python = await _ensure_runtime_venv(state)
            if install_requirements:
                if using_builtin_model_app:
                    await _install_builtin_model_requirements(state)
                await _install_requirements(state)

            env = os.environ.copy()
            proxy_path = f"/api/{repo.repo_type}s/{repo.namespace}/{repo.name}/runtime/proxy"
            env.update(
                {
                    "PORT": str(state.port),
                    "SPACE_PORT": str(state.port),
                    "GRADIO_SERVER_NAME": "0.0.0.0",
                    "GRADIO_SERVER_PORT": str(state.port),
                    "GRADIO_ROOT_PATH": proxy_path,
                    "CN_MODEL_HUB_REPO_TYPE": repo.repo_type,
                    "CN_MODEL_HUB_REPO_ID": f"{repo.namespace}/{repo.name}",
                    "CN_MODEL_HUB_SPACE_ID": f"{repo.namespace}/{repo.name}",
                    "CN_MODEL_HUB_SPACE_REVISION": revision,
                    "CN_MODEL_HUB_SPACE_COMMIT": commit_id,
                    "CN_MODEL_HUB_REPO_REVISION": revision,
                    "CN_MODEL_HUB_REPO_COMMIT": commit_id,
                    "LOCAL_MODEL_PATH": str(workdir),
                    "MLFLOW_TRACKING_URI": cfg.app.mlflow_tracking_uri,
                    "MLFLOW_EXPERIMENT_NAME": repo.mlflow_experiment_name or "",
                    "MLFLOW_EXPERIMENT_ID": repo.mlflow_experiment_id or "",
                    "PYTHONUNBUFFERED": "1",
                }
            )
            state.process = await asyncio.create_subprocess_exec(
                str(runtime_python),
                str(app_file.resolve()),
                cwd=str(workdir),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            asyncio.create_task(_read_process_output(state))
            await _wait_for_http(state)
            return state
        except Exception as exc:
            state.status = "error"
            state.message = str(exc)
            state.append_log(f"Runtime start failed: {exc}")
            if state.process and state.process.returncode is None:
                state.process.terminate()
            raise


async def stop_runtime_for_repo(
    repo_type: str,
    namespace: str,
    name: str,
    reason: str = "repository updated",
) -> None:
    key = _runtime_key(repo_type, namespace, name)
    if _remote_enabled():
        remote_key = _remote_runtime_key(repo_type, namespace, name)
        try:
            data = await _remote_agent_stop(remote_key, reason)
            _remote_statuses[key] = data
        except Exception as exc:
            logger.warning(
                f"Repository updated, but failed to stop remote runtime {remote_key}: {exc}"
            )
        return

    state = _runtimes.get(key)
    if state and state.process and state.process.returncode is None:
        state.process.terminate()
        state.status = "stopped"
        state.message = f"Runtime stopped: {reason}."


@router.get("/{repo_type}s/{namespace}/{name}/runtime")
async def get_runtime_status(
    repo_type: str,
    namespace: str,
    name: str,
    user: User | None = Depends(get_optional_user),
):
    repo_type = _normalize_repo_type(repo_type)
    repo = _repo_or_404(repo_type, namespace, name)
    check_repo_read_permission(repo, user)
    if _remote_enabled():
        key = _runtime_key(repo_type, namespace, name)
        remote_key = _remote_runtime_key(repo_type, namespace, name)
        try:
            data = await _remote_agent_get_status(remote_key)
            _remote_statuses[key] = data
        except Exception as exc:
            logger.warning(f"Failed to fetch remote runtime status {remote_key}: {exc}")
            data = _remote_statuses.get(key)
        return _public_remote_status(repo, data)
    return _public_status(_runtimes.get(_runtime_key(repo_type, namespace, name)))


@router.get("/runtime/demos")
async def list_runtime_demos(user: User | None = Depends(get_optional_user)):
    demos = []
    query = (
        Repository.select()
        .where(Repository.repo_type.in_(sorted(SUPPORTED_RUNTIME_REPO_TYPES)))
        .order_by(Repository.created_at.desc())
        .limit(100)
    )
    for repo in query:
        state = _runtimes.get(_runtime_key(repo.repo_type, repo.namespace, repo.name))
        if not repo:
            continue
        try:
            check_repo_read_permission(repo, user)
        except (RepoReadDeniedError, HTTPException):
            continue
        demos.append(_serialize_demo(repo, state))

    status_order = {"running": 0, "starting": 1, "error": 2, "stopped": 3}
    demos.sort(key=lambda demo: demo.get("full_id", ""))
    demos.sort(
        key=lambda demo: demo.get("last_modified") or demo.get("created_at") or "",
        reverse=True,
    )
    demos.sort(key=lambda demo: status_order.get(demo.get("status"), 9))
    return {"demos": demos}


@router.post("/{repo_type}s/{namespace}/{name}/runtime/start")
async def start_runtime(
    repo_type: str,
    namespace: str,
    name: str,
    payload: RuntimeStartPayload | None = None,
    user: User = Depends(get_current_user),
):
    repo_type = _normalize_repo_type(repo_type)
    repo = _repo_or_404(repo_type, namespace, name)
    check_repo_write_permission(repo, user)
    body = payload or RuntimeStartPayload()
    install = (
        cfg.app.space_runtime_install_requirements
        if body.install_requirements is None
        else body.install_requirements
    )
    try:
        if _remote_enabled():
            data = await _start_remote_runtime(repo, body.revision, install)
            return _public_remote_status(repo, data)
        state = await _start_runtime(repo, body.revision, install)
        return _public_status(state)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to start {repo_type} runtime {namespace}/{name}", exc)
        state = _runtimes.get(_runtime_key(repo_type, namespace, name))
        if state:
            return _public_status(state)
        raise HTTPException(500, detail={"error": str(exc)})


@router.post("/{repo_type}s/{namespace}/{name}/runtime/stop")
async def stop_runtime(
    repo_type: str,
    namespace: str,
    name: str,
    user: User = Depends(get_current_user),
):
    repo_type = _normalize_repo_type(repo_type)
    repo = _repo_or_404(repo_type, namespace, name)
    check_repo_write_permission(repo, user)
    if _remote_enabled():
        remote_key = _remote_runtime_key(repo_type, namespace, name)
        data = await _remote_agent_stop(remote_key, "manual stop")
        _remote_statuses[_runtime_key(repo_type, namespace, name)] = data
        return _public_remote_status(repo, data)
    state = _runtimes.get(_runtime_key(repo_type, namespace, name))
    if state and state.process and state.process.returncode is None:
        state.process.terminate()
        state.status = "stopped"
        state.message = "Runtime stopped."
    return _public_status(state)


@router.api_route(
    "/{repo_type}s/{namespace}/{name}/runtime/proxy",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
@router.api_route(
    "/{repo_type}s/{namespace}/{name}/runtime/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy_runtime(
    repo_type: str,
    namespace: str,
    name: str,
    request: Request,
    path: str = "",
    user: User | None = Depends(get_optional_user),
):
    repo_type = _normalize_repo_type(repo_type)
    repo = _repo_or_404(repo_type, namespace, name)
    check_repo_read_permission(repo, user)
    if _remote_enabled():
        remote_key = _remote_runtime_key(repo_type, namespace, name)
        target_url = _remote_agent_url(
            f"/api/runtime/proxy/{quote(remote_key, safe='')}/{path}"
        )
        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
            and key.lower() not in {"host", "accept-encoding", "authorization"}
        }
        headers.update(_remote_headers())
        headers["accept-encoding"] = "identity"
        async with httpx.AsyncClient(follow_redirects=False, timeout=None) as client:
            upstream = await client.request(
                request.method,
                target_url,
                content=await request.body(),
                headers=headers,
            )
        response_headers = {
            key: value
            for key, value in upstream.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
        }
        location = response_headers.get("location") or response_headers.get("Location")
        if location and location.startswith("/"):
            response_headers["location"] = (
                f"/api/{repo_type}s/{namespace}/{name}/runtime/proxy{location}"
            )
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
            media_type=upstream.headers.get("content-type"),
        )
    state = _runtimes.get(_runtime_key(repo_type, namespace, name))
    if not state or state.status not in {"running", "starting"}:
        raise HTTPException(404, detail={"error": "Runtime is not running"})

    target_url = urljoin(state.app_url, path)
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and key.lower() not in {"host", "accept-encoding"}
    }
    headers["accept-encoding"] = "identity"
    async with httpx.AsyncClient(follow_redirects=False, timeout=None) as client:
        upstream = await client.request(
            request.method,
            target_url,
            content=await request.body(),
            headers=headers,
        )

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    location = response_headers.get("location") or response_headers.get("Location")
    if location and location.startswith("/"):
        response_headers["location"] = (
            f"/api/{repo_type}s/{namespace}/{name}/runtime/proxy{location}"
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
