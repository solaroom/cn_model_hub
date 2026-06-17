from __future__ import annotations

import asyncio
import os
import shutil
import socket
import tarfile
import time
from collections import deque
from pathlib import Path
from typing import Any

import httpx
import torch
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
RUNTIME_AGENT_API_KEY = os.getenv("RUNTIME_AGENT_API_KEY", "")
DEFAULT_RUNTIME_ROOT = os.getenv(
    "CN_MODEL_HUB_RUNTIME_ROOT", "/root/autodl-tmp/cn-model-hub-runtimes"
)
RUNTIME_LOG_LINES = 5000
SKIP_TORCH_INSTALL = os.getenv("CN_MODEL_HUB_RUNTIME_SKIP_TORCH_INSTALL", "true").lower() == "true"


app = FastAPI(title="cn_model_hub Runtime Agent", version="1.2.0")
runtimes: dict[str, dict[str, Any]] = {}
active_runtime_key: str | None = None
runtime_lock = asyncio.Lock()


class RuntimeStartRequest(BaseModel):
    runtime_key: str
    repo_type: str
    repo_id: str
    revision: str = "main"
    commit_id: str
    remote_root: str | None = None
    app_entry: str = "app.py"
    using_builtin_model_app: bool = False
    install_requirements: bool = True
    env: dict[str, str] = {}


class RuntimeStopRequest(BaseModel):
    runtime_key: str
    reason: str = "manual stop"


BUILTIN_MODEL_APP = r'''
from __future__ import annotations

import os
from pathlib import Path

import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_PATH = Path(os.getenv("LOCAL_MODEL_PATH", ".")).resolve()
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "128"))
_tokenizer = None
_model = None
_device = "cpu"


def _pick_device():
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_model():
    global _tokenizer, _model, _device
    if _model is not None and _tokenizer is not None:
        return _tokenizer, _model, _device
    _device = _pick_device()
    dtype = torch.float16 if _device == "cuda" else torch.float32
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True, local_files_only=True)
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=dtype,
        trust_remote_code=True,
        local_files_only=True,
    )
    _model.to(_device)
    _model.eval()
    return _tokenizer, _model, _device


def chat(message, history):
    try:
        tokenizer, model, device = _load_model()
        messages = [{"role": "user", "content": message}]
        if hasattr(tokenizer, "apply_chat_template"):
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            text = message
        inputs = tokenizer([text], return_tensors="pt").to(device)
        inputs.pop("token_type_ids", None)
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        output_ids = generated[0][inputs.input_ids.shape[-1]:]
        return tokenizer.decode(output_ids, skip_special_tokens=True).strip() or "模型没有生成内容。"
    except Exception as exc:
        return f"远程模型启动或推理失败。\n\n模型目录：{MODEL_PATH}\n\n错误：{exc}"


demo = gr.ChatInterface(fn=chat, title="远程 GPU 模型 Demo", type="messages")

if __name__ == "__main__":
    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", "7860"))),
        root_path=os.getenv("GRADIO_ROOT_PATH") or None,
    )
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


def require_runtime_api_key(authorization: str | None = Header(default=None)) -> None:
    if RUNTIME_AGENT_API_KEY and authorization != f"Bearer {RUNTIME_AGENT_API_KEY}":
        raise HTTPException(status_code=401, detail="invalid or missing runtime API key")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "cuda": torch.cuda.is_available(),
        "cuda_available": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "active_runtime_key": active_runtime_key,
    }


def runtime_dir(runtime_key: str, root: str | None = None) -> Path:
    return Path(root or DEFAULT_RUNTIME_ROOT).expanduser().resolve() / runtime_key


def public_runtime_status(runtime_key: str) -> dict[str, Any]:
    state = runtimes.get(runtime_key)
    root = runtime_dir(runtime_key)
    commit_file = root / ".commit"
    commit_id = commit_file.read_text(encoding="utf-8").strip() if commit_file.exists() else ""
    if not state:
        return {
            "status": "stopped",
            "runtime_key": runtime_key,
            "commit_id": commit_id,
            "message": "Runtime is stopped.",
            "logs": [],
            "active_runtime_key": active_runtime_key,
        }
    proc = state.get("process")
    if state.get("status") == "running" and proc and proc.returncode is not None:
        state["status"] = "stopped"
        state["message"] = f"Runtime process exited with code {proc.returncode}."
    return {
        "status": state.get("status", "stopped"),
        "runtime_key": runtime_key,
        "repo_id": state.get("repo_id"),
        "revision": state.get("revision"),
        "commit_id": state.get("commit_id") or commit_id,
        "pid": proc.pid if proc else None,
        "port": state.get("port"),
        "message": state.get("message", ""),
        "logs": list(state.get("logs") or []),
        "log_limit": RUNTIME_LOG_LINES,
        "active_runtime_key": active_runtime_key,
        "cuda_available": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def safe_extract(archive_path: Path, target: Path) -> None:
    target_resolved = target.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            member_path = (target / member.name).resolve()
            if target_resolved not in [member_path, *member_path.parents]:
                raise RuntimeError(f"Unsafe archive member: {member.name}")
        archive.extractall(target)


def append_log(state: dict[str, Any], line: str) -> None:
    logs = state.setdefault("logs", deque(maxlen=RUNTIME_LOG_LINES))
    logs.append(line.rstrip())


async def read_process_output(state: dict[str, Any]) -> None:
    proc = state.get("process")
    if not proc or not proc.stdout:
        return
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        append_log(state, line.decode(errors="replace"))


def free_port() -> int:
    for port in range(7861, 7900):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def run_logged(state: dict[str, Any], command: list[str], cwd: Path) -> int:
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    if proc.stdout:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            append_log(state, line.decode(errors="replace"))
    return await proc.wait()


async def ensure_venv(state: dict[str, Any], root: Path) -> Path:
    python = root / "venv" / "bin" / "python"
    if python.exists():
        return python
    code = await run_logged(
        state,
        ["/root/miniconda3/bin/python", "-m", "venv", "--system-site-packages", str(root / "venv")],
        root,
    )
    if code != 0:
        raise RuntimeError(f"venv creation failed with code {code}")
    return python


def filtered_requirements(requirements: Path) -> Path:
    if not SKIP_TORCH_INSTALL:
        return requirements
    filtered = requirements.with_name(".requirements.runtime-filtered.txt")
    blocked = ("torch", "torchvision", "torchaudio")
    kept = []
    for line in requirements.read_text(encoding="utf-8").splitlines():
        stripped = line.strip().lower()
        if any(stripped == name or stripped.startswith(name + "=") or stripped.startswith(name + ">") for name in blocked):
            continue
        kept.append(line)
    filtered.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return filtered


async def install_requirements(state: dict[str, Any], root: Path, current: Path, builtin: bool) -> None:
    python = await ensure_venv(state, root)
    if builtin:
        append_log(state, "Installing Gradio for built-in runtime ...")
        code = await run_logged(state, [str(python), "-m", "pip", "install", "gradio>=4.44,<6"], current)
        if code != 0:
            raise RuntimeError(f"Gradio install failed with code {code}")
    requirements = current / "requirements.txt"
    if requirements.exists():
        req = filtered_requirements(requirements)
        append_log(state, f"Installing {req.name} ...")
        code = await run_logged(state, [str(python), "-m", "pip", "install", "-r", str(req)], current)
        if code != 0:
            raise RuntimeError(f"requirements install failed with code {code}")


async def wait_for_http(state: dict[str, Any], timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient(timeout=1.5) as client:
        while time.monotonic() < deadline:
            proc = state.get("process")
            if proc and proc.returncode is not None:
                state["status"] = "error"
                state["message"] = f"Runtime process exited with code {proc.returncode}."
                return
            try:
                response = await client.get(f"http://127.0.0.1:{state['port']}/")
                if response.status_code < 500:
                    state["status"] = "running"
                    state["message"] = "Runtime is running."
                    return
            except Exception:
                await asyncio.sleep(0.5)
    state["status"] = "starting"
    state["message"] = "Runtime process started, but HTTP is still warming up."


async def stop_runtime_process(runtime_key: str, reason: str) -> dict[str, Any]:
    global active_runtime_key
    state = runtimes.get(runtime_key)
    if state:
        proc = state.get("process")
        if proc and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=10)
            except asyncio.TimeoutError:
                proc.kill()
        state["status"] = "stopped"
        state["message"] = f"Runtime stopped: {reason}."
    if active_runtime_key == runtime_key:
        active_runtime_key = None
    return public_runtime_status(runtime_key)


@app.get("/api/runtime/status/{runtime_key}", dependencies=[Depends(require_runtime_api_key)])
async def runtime_status(runtime_key: str) -> dict[str, Any]:
    return public_runtime_status(runtime_key)


@app.post("/api/runtime/stop", dependencies=[Depends(require_runtime_api_key)])
async def runtime_stop(req: RuntimeStopRequest) -> dict[str, Any]:
    return await stop_runtime_process(req.runtime_key, req.reason)


@app.post("/api/runtime/start", dependencies=[Depends(require_runtime_api_key)])
async def runtime_start(req: RuntimeStartRequest) -> dict[str, Any]:
    global active_runtime_key
    async with runtime_lock:
        if active_runtime_key and active_runtime_key != req.runtime_key:
            return {
                "status": "busy",
                "message": f"GPU is busy. Current runtime: {active_runtime_key}",
                "active_runtime_key": active_runtime_key,
            }
        state = runtimes.get(req.runtime_key)
        proc = state.get("process") if state else None
        if proc and proc.returncode is None and state.get("commit_id") == req.commit_id:
            return public_runtime_status(req.runtime_key)

        root = runtime_dir(req.runtime_key, req.remote_root)
        root.mkdir(parents=True, exist_ok=True)
        current = root / "current"
        commit_file = root / ".commit"
        state = {
            "status": "starting",
            "runtime_key": req.runtime_key,
            "repo_id": req.repo_id,
            "revision": req.revision,
            "commit_id": req.commit_id,
            "logs": deque(maxlen=RUNTIME_LOG_LINES),
        }
        runtimes[req.runtime_key] = state
        try:
            if not current.exists() or not commit_file.exists() or commit_file.read_text(encoding="utf-8").strip() != req.commit_id:
                source = root / "incoming" / "source.tar.gz"
                if not source.exists():
                    raise RuntimeError(f"Missing uploaded runtime package: {source}")
                incoming_current = root / "incoming" / "current"
                if incoming_current.exists():
                    shutil.rmtree(incoming_current)
                incoming_current.mkdir(parents=True, exist_ok=True)
                safe_extract(source, incoming_current)
                if current.exists():
                    shutil.rmtree(current)
                shutil.move(str(incoming_current), str(current))
                commit_file.write_text(req.commit_id, encoding="utf-8")
                try:
                    source.unlink()
                except OSError:
                    pass

            app_file = current / req.app_entry
            if req.using_builtin_model_app and not app_file.exists():
                app_file = current / ".cn_model_hub_remote_model_app.py"
                app_file.write_text(BUILTIN_MODEL_APP, encoding="utf-8")
            if not app_file.exists():
                raise RuntimeError(f"Runtime app entry not found: {req.app_entry}")

            if req.install_requirements:
                await install_requirements(state, root, current, req.using_builtin_model_app)
            python = await ensure_venv(state, root)
            port = free_port()
            env = os.environ.copy()
            env.update(req.env)
            env.update(
                {
                    "PORT": str(port),
                    "SPACE_PORT": str(port),
                    "GRADIO_SERVER_NAME": "0.0.0.0",
                    "GRADIO_SERVER_PORT": str(port),
                    "GRADIO_ROOT_PATH": f"/api/runtime/proxy/{req.runtime_key}",
                    "LOCAL_MODEL_PATH": str(current),
                    "PYTHONUNBUFFERED": "1",
                }
            )
            state["port"] = port
            state["process"] = await asyncio.create_subprocess_exec(
                str(python),
                str(app_file),
                cwd=str(current),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            active_runtime_key = req.runtime_key
            asyncio.create_task(read_process_output(state))
            await wait_for_http(state)
            if state.get("status") == "error":
                active_runtime_key = None
            return public_runtime_status(req.runtime_key)
        except Exception as exc:
            state["status"] = "error"
            state["message"] = str(exc)
            append_log(state, f"Runtime start failed: {exc}")
            if active_runtime_key == req.runtime_key:
                active_runtime_key = None
            return public_runtime_status(req.runtime_key)


@app.api_route(
    "/api/runtime/proxy/{runtime_key}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    dependencies=[Depends(require_runtime_api_key)],
)
@app.api_route(
    "/api/runtime/proxy/{runtime_key}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    dependencies=[Depends(require_runtime_api_key)],
)
async def runtime_proxy(runtime_key: str, request: Request, path: str = "") -> Response:
    state = runtimes.get(runtime_key)
    if not state or state.get("status") not in {"running", "starting"}:
        raise HTTPException(404, detail="Runtime is not running")
    target_url = f"http://127.0.0.1:{state['port']}/{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() not in {"host", "accept-encoding", "authorization"}
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
        response_headers["location"] = f"/api/runtime/proxy/{runtime_key}{location}"
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
