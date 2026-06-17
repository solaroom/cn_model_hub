"""Quick local model evaluation endpoints."""

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cn_model_hub.api.repo.utils.hf import hf_repo_not_found
from cn_model_hub.api.space_runtime import (
    BUILTIN_QWEN_LOCAL_REQUIREMENTS,
    PYTORCH_CPU_INDEX_URL,
    _materialize_repo,
    _runtime_root,
)
from cn_model_hub.auth.dependencies import get_current_user, get_optional_user
from cn_model_hub.auth.permissions import (
    RepoReadDeniedError,
    check_repo_read_permission,
    check_repo_write_permission,
)
from cn_model_hub.db import EvaluationRun, Repository, User
from cn_model_hub.db_operations import get_repository
from cn_model_hub.logger import get_logger

logger = get_logger("EVALUATIONS")
router = APIRouter()

SUPPORTED_DATASET_REPO = "C-Eval"
LEGACY_SUPPORTED_DATASET_REPOS = {"qwen_demo/c-eval"}
BUILTIN_CEVAL_RELATIVE_PATH = "examples/datasets/c-eval/quick_eval/ceval_20.jsonl"
SUPPORTED_MODEL_FAMILY = "qwen2.5"
SUPPORTED_LEADERBOARD = "generative_llm"
QUICK_EVAL_TOTAL = 20
EVAL_TIMEOUT_SECONDS = 20 * 60

EVAL_SCRIPT = r'''
import json
import re
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_dir = Path(sys.argv[1]).resolve()
dataset_path = Path(sys.argv[2]).resolve()
output_path = Path(sys.argv[3]).resolve()

tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)


def load_model():
    try:
        return AutoModelForCausalLM.from_pretrained(
            model_dir,
            local_files_only=True,
            dtype=torch.float32,
        )
    except TypeError as exc:
        if "dtype" not in str(exc):
            raise
        return AutoModelForCausalLM.from_pretrained(
            model_dir,
            local_files_only=True,
            torch_dtype=torch.float32,
        )


model = load_model()
model.eval()
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)


def make_prompt(item):
    choices = item["choices"]
    return (
        "请完成下面的中文单项选择题。只输出一个大写字母 A、B、C 或 D，不要解释。\n\n"
        f"科目：{item.get('subject', '')}\n"
        f"题目：{item['question']}\n"
        f"A. {choices['A']}\n"
        f"B. {choices['B']}\n"
        f"C. {choices['C']}\n"
        f"D. {choices['D']}\n"
        "答案："
    )


def predict(item):
    prompt = make_prompt(item)
    if getattr(tokenizer, "chat_template", None):
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    else:
        text = prompt
    inputs = tokenizer(text, return_tensors="pt").to(device)
    inputs.pop("token_type_ids", None)
    with torch.no_grad():
        generated = model.generate(
            **inputs,
            max_new_tokens=4,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = generated[0][inputs["input_ids"].shape[-1]:]
    answer_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    match = re.search(r"[ABCD]", answer_text.upper())
    return (match.group(0) if match else ""), answer_text


items = []
with dataset_path.open("r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line:
            items.append(json.loads(line))

details = []
correct = 0
for item in items:
    pred, raw = predict(item)
    expected = str(item["answer"]).strip().upper()
    ok = pred == expected
    correct += int(ok)
    details.append(
        {
            "id": item.get("id"),
            "subject": item.get("subject"),
            "answer": expected,
            "prediction": pred,
            "raw_prediction": raw,
            "correct": ok,
        }
    )

result = {
    "total": len(items),
    "correct": correct,
    "accuracy": correct / len(items) if items else 0.0,
    "details": details,
}
output_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
'''


class QuickEvalRequest(BaseModel):
    revision: str = "main"
    dataset_repo: str = SUPPORTED_DATASET_REPO


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _serialize_repo(repo: Repository) -> dict[str, Any]:
    return {
        "repo_type": repo.repo_type,
        "namespace": repo.namespace,
        "name": repo.name,
        "full_id": repo.full_id,
    }


def _serialize_run(run: EvaluationRun, rank: int | None = None) -> dict[str, Any]:
    result = None
    if run.result_json:
        try:
            result = json.loads(run.result_json)
        except json.JSONDecodeError:
            result = None
    return {
        "id": run.id,
        "repository": _serialize_repo(run.repository),
        "benchmark": run.benchmark,
        "leaderboard": run.leaderboard,
        "leaderboard_label": _leaderboard_label(run.leaderboard),
        "model_family": run.model_family,
        "dataset_repo": run.dataset_repo,
        "status": run.status,
        "total": run.total,
        "correct": run.correct,
        "accuracy": run.accuracy,
        "revision": run.revision,
        "commit_id": run.commit_id,
        "result": result,
        "error": run.error,
        "rank": rank,
        "created_at": _iso(run.created_at),
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
    }


def _leaderboard_label(leaderboard: str) -> str:
    labels = {
        SUPPORTED_LEADERBOARD: "生成式大语言模型",
    }
    return labels.get(leaderboard, leaderboard)


def _repo_supports_qwen25(repo: Repository) -> bool:
    repo_id = f"{repo.namespace}/{repo.name}".lower()
    return "qwen2.5" in repo_id or "qwen-2.5" in repo_id or "qwen" in repo_id


def _split_repo_id(repo_id: str) -> tuple[str, str]:
    parts = repo_id.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HTTPException(400, detail={"error": "dataset_repo must look like namespace/name"})
    return parts[0], parts[1]


def _find_ceval_dataset_repo(dataset_repo_id: str) -> Repository | None:
    if "/" in dataset_repo_id:
        ds_namespace, ds_name = _split_repo_id(dataset_repo_id)
        return get_repository("dataset", ds_namespace, ds_name)

    wanted = {dataset_repo_id.lower(), "c-eval", "ceval"}
    for repo in (
        Repository.select()
        .where(Repository.repo_type == "dataset")
        .order_by(Repository.created_at.desc())
    ):
        if repo.name.lower() in wanted or repo.full_id.lower() in wanted:
            return repo
    return None


def _project_roots() -> list[Path]:
    roots = [Path.cwd()]
    try:
        roots.append(Path(__file__).resolve().parents[3])
    except IndexError:
        pass
    roots.append(Path("/app"))
    seen: set[Path] = set()
    result: list[Path] = []
    for root in roots:
        root = root.resolve()
        if root in seen:
            continue
        seen.add(root)
        result.append(root)
    return result


def _builtin_ceval_dataset_path() -> Path | None:
    configured = os.getenv("CN_MODEL_HUB_CEVAL_QUICK_EVAL_PATH")
    candidates = [Path(configured).expanduser()] if configured else []
    candidates.extend(root / BUILTIN_CEVAL_RELATIVE_PATH for root in _project_roots())
    for path in candidates:
        if path.exists() and path.is_file():
            return path.resolve()
    return None


async def _resolve_ceval_dataset_path(dataset_repo_id: str) -> Path:
    dataset_repo = _find_ceval_dataset_repo(dataset_repo_id)
    if dataset_repo:
        dataset_dir, _ = await _materialize_repo(dataset_repo, "main")
        dataset_path = dataset_dir / "quick_eval" / "ceval_20.jsonl"
        if dataset_path.exists():
            return dataset_path
        logger.warning(
            "C-Eval dataset repo exists but quick_eval/ceval_20.jsonl is missing; "
            "falling back to built-in quick eval subset"
        )

    builtin = _builtin_ceval_dataset_path()
    if builtin:
        return builtin
    raise RuntimeError(
        f"未找到评测数据集 {dataset_repo_id}，且项目内置 C-Eval 20题文件不存在"
    )


async def _ensure_eval_python() -> Path:
    root = _runtime_root() / "_quick_eval"
    venv = root / "venv"
    python = venv / "bin" / "python"
    marker = root / ".requirements-installed"
    root.mkdir(parents=True, exist_ok=True)
    if not python.exists():
        process = await asyncio.create_subprocess_exec(
            "uv",
            "venv",
            "--seed",
            str(venv),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        output, _ = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(
                "evaluation venv creation failed: "
                + output.decode(errors="replace")[-2000:]
            )

    requirements = "\n".join(
        ["torch>=2.1", *BUILTIN_QWEN_LOCAL_REQUIREMENTS, "safetensors>=0.4"]
    )
    digest = hashlib.sha256(requirements.encode()).hexdigest()
    if marker.exists() and marker.read_text(encoding="utf-8") == digest:
        return python

    torch_process = await asyncio.create_subprocess_exec(
        "uv",
        "pip",
        "install",
        "--python",
        str(python),
        "--index-url",
        PYTORCH_CPU_INDEX_URL,
        "torch>=2.1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    torch_output, _ = await torch_process.communicate()
    if torch_process.returncode != 0:
        raise RuntimeError(
            "evaluation torch install failed: "
            + torch_output.decode(errors="replace")[-2000:]
        )

    reqs = [pkg for pkg in BUILTIN_QWEN_LOCAL_REQUIREMENTS if not pkg.startswith("torch")]
    deps_process = await asyncio.create_subprocess_exec(
        "uv",
        "pip",
        "install",
        "--python",
        str(python),
        *reqs,
        "safetensors>=0.4",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    deps_output, _ = await deps_process.communicate()
    if deps_process.returncode != 0:
        raise RuntimeError(
            "evaluation dependency install failed: "
            + deps_output.decode(errors="replace")[-2000:]
        )
    marker.write_text(digest, encoding="utf-8")
    return python


async def _run_evaluation(run_id: int) -> None:
    run = EvaluationRun.get_by_id(run_id)
    run.status = "running"
    run.started_at = _utc_now()
    run.save()

    try:
        model_dir, commit_id = await _materialize_repo(run.repository, run.revision)
        config_path = model_dir / "config.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            model_type = str(config.get("model_type", "")).lower()
            architectures = " ".join(config.get("architectures") or []).lower()
            if "qwen2" not in model_type and "qwen" not in architectures:
                raise RuntimeError("当前快速评测只支持 Qwen2.5/Qwen2 Transformers 模型")

        dataset_path = await _resolve_ceval_dataset_path(run.dataset_repo)

        workdir = _runtime_root() / "_quick_eval" / f"run-{run.id}"
        workdir.mkdir(parents=True, exist_ok=True)
        script_path = workdir / "eval_qwen25.py"
        output_path = workdir / "result.json"
        script_path.write_text(EVAL_SCRIPT, encoding="utf-8")
        python = await _ensure_eval_python()

        env = os.environ.copy()
        env.update(
            {
                "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_OFFLINE": "1",
                "TOKENIZERS_PARALLELISM": "false",
                "PYTHONUNBUFFERED": "1",
            }
        )
        process = await asyncio.create_subprocess_exec(
            str(python),
            str(script_path),
            str(model_dir),
            str(dataset_path),
            str(output_path),
            cwd=str(workdir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            output, _ = await asyncio.wait_for(
                process.communicate(), timeout=EVAL_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise RuntimeError("评测超时，请稍后减少题量或使用更快硬件") from exc

        if process.returncode != 0:
            raise RuntimeError(
                "评测脚本执行失败: " + output.decode(errors="replace")[-3000:]
            )
        result = json.loads(output_path.read_text(encoding="utf-8"))
        run = EvaluationRun.get_by_id(run_id)
        run.status = "completed"
        run.commit_id = commit_id
        run.total = int(result.get("total") or QUICK_EVAL_TOTAL)
        run.correct = int(result.get("correct") or 0)
        run.accuracy = float(result.get("accuracy") or 0.0)
        run.result_json = json.dumps(result, ensure_ascii=False)
        run.finished_at = _utc_now()
        run.error = None
        run.save()
    except Exception as exc:
        logger.exception(f"Quick evaluation {run_id} failed", exc)
        run = EvaluationRun.get_by_id(run_id)
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = _utc_now()
        run.save()


@router.post("/{repo_type}s/{namespace}/{name}/evaluations/quick")
async def start_quick_evaluation(
    repo_type: str,
    namespace: str,
    name: str,
    payload: QuickEvalRequest | None = None,
    user: User = Depends(get_current_user),
):
    repo = get_repository(repo_type, namespace, name)
    if not repo:
        return hf_repo_not_found(f"{namespace}/{name}", repo_type)
    if repo.repo_type != "model":
        raise HTTPException(400, detail={"error": "快速评测当前只支持模型仓库"})
    check_repo_write_permission(repo, user)
    body = payload or QuickEvalRequest()
    if (
        body.dataset_repo != SUPPORTED_DATASET_REPO
        and body.dataset_repo not in LEGACY_SUPPORTED_DATASET_REPOS
    ):
        raise HTTPException(
            400,
            detail={"error": f"当前快速评测只支持 {SUPPORTED_DATASET_REPO}"},
        )
    if not _repo_supports_qwen25(repo):
        raise HTTPException(
            400,
            detail={"error": "当前快速评测只支持 Qwen2.5 类型模型"},
        )

    existing = (
        EvaluationRun.select()
        .where(
            (EvaluationRun.repository == repo)
            & (EvaluationRun.status.in_(["pending", "running"]))
        )
        .order_by(EvaluationRun.created_at.desc())
        .first()
    )
    if existing:
        return _serialize_run(existing)

    run = EvaluationRun.create(
        repository=repo,
        triggered_by=user,
        benchmark="C-Eval",
        leaderboard=SUPPORTED_LEADERBOARD,
        model_family=SUPPORTED_MODEL_FAMILY,
        dataset_repo=body.dataset_repo,
        revision=body.revision,
        total=QUICK_EVAL_TOTAL,
        status="pending",
    )
    asyncio.create_task(_run_evaluation(run.id))
    return _serialize_run(run)


@router.get("/{repo_type}s/{namespace}/{name}/evaluations/quick")
async def list_quick_evaluations(
    repo_type: str,
    namespace: str,
    name: str,
    user: User | None = Depends(get_optional_user),
):
    repo = get_repository(repo_type, namespace, name)
    if not repo:
        return hf_repo_not_found(f"{namespace}/{name}", repo_type)
    check_repo_read_permission(repo, user)
    runs = (
        EvaluationRun.select()
        .where(EvaluationRun.repository == repo)
        .order_by(EvaluationRun.created_at.desc())
        .limit(20)
    )
    return {
        "runs": [_serialize_run(run) for run in runs],
        "supported": repo.repo_type == "model" and _repo_supports_qwen25(repo),
        "benchmark": "C-Eval",
        "total": QUICK_EVAL_TOTAL,
        "dataset_repo": SUPPORTED_DATASET_REPO,
        "dataset_available": _builtin_ceval_dataset_path() is not None
        or _find_ceval_dataset_repo(SUPPORTED_DATASET_REPO) is not None,
        "leaderboard": SUPPORTED_LEADERBOARD,
        "leaderboard_label": _leaderboard_label(SUPPORTED_LEADERBOARD),
    }


@router.get("/leaderboards/{leaderboard}")
async def get_leaderboard(
    leaderboard: str,
    user: User | None = Depends(get_optional_user),
):
    if leaderboard not in {SUPPORTED_LEADERBOARD, "generative-llm"}:
        raise HTTPException(404, detail={"error": "排行榜不存在"})
    normalized = SUPPORTED_LEADERBOARD
    query = (
        EvaluationRun.select(EvaluationRun, Repository)
        .join(Repository)
        .where(
            (EvaluationRun.leaderboard == normalized)
            & (EvaluationRun.status == "completed")
        )
        .order_by(EvaluationRun.accuracy.desc(), EvaluationRun.finished_at.asc())
    )
    entries = []
    rank = 0
    for run in query:
        try:
            check_repo_read_permission(run.repository, user)
        except RepoReadDeniedError:
            continue
        rank += 1
        entries.append(_serialize_run(run, rank=rank))
    return {
        "leaderboard": normalized,
        "label": _leaderboard_label(normalized),
        "metric": "accuracy",
        "metric_label": "C-Eval 20题准确率",
        "ranking_rule": "按准确率从高到低排序；准确率相同则先完成评测的模型靠前。",
        "entries": entries,
    }
