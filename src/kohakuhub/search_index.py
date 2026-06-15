"""Meilisearch-backed repository search index."""

from __future__ import annotations

import time
from typing import Any

from kohakuhub.config import cfg
from kohakuhub.db import Repository
from kohakuhub.logger import get_logger

logger = get_logger("SEARCH_INDEX")

REPOSITORY_INDEX = "repositories"

_client: Any | None = None
_settings_initialized = False

_ALIAS_TERMS: dict[str, tuple[str, ...]] = {
    "qwen": ("千问", "通义", "通义千问", "tongyi"),
    "chatglm": ("智谱", "清言", "glm", "zhipu"),
    "glm": ("智谱", "清言", "chatglm", "zhipu"),
    "baichuan": ("百川",),
    "internlm": ("书生", "浦语"),
    "hunyuan": ("混元",),
    "ernie": ("文心", "wenxin"),
    "kimi": ("月之暗面", "moonshot"),
    "moonshot": ("月之暗面", "kimi"),
    "deepseek": ("深度求索", "深度搜索"),
    "yi": ("零一万物", "01-ai", "01ai"),
    "embedding": ("嵌入", "向量"),
    "rerank": ("重排", "reranker"),
    "vlm": ("多模态", "视觉", "图像", "vision"),
    "vision": ("多模态", "视觉", "图像", "vlm"),
    "chat": ("对话", "聊天", "指令", "instruct"),
    "instruct": ("指令", "对话", "聊天"),
    "chinese": ("中文", "汉语", "zh"),
    "zh": ("中文", "汉语", "chinese"),
}


def is_enabled() -> bool:
    return bool(cfg.search.meilisearch_enabled and cfg.search.meilisearch_url)


def get_client() -> Any | None:
    """Return a Meilisearch client when configured and importable."""
    global _client
    if not is_enabled():
        return None
    if _client is not None:
        return _client
    try:
        import meilisearch
    except ImportError:
        logger.warning("Meilisearch enabled but the meilisearch package is not installed")
        return None

    _client = meilisearch.Client(
        cfg.search.meilisearch_url,
        cfg.search.meilisearch_api_key or None,
        timeout=cfg.search.meilisearch_timeout_seconds,
    )
    return _client


def get_index() -> Any | None:
    client = get_client()
    if client is None:
        return None
    return client.index(REPOSITORY_INDEX)


def wait_for_task(task: Any) -> None:
    client = get_client()
    task_uid = None
    if isinstance(task, dict):
        task_uid = task.get("taskUid") or task.get("uid")
    else:
        task_uid = getattr(task, "task_uid", None) or getattr(task, "uid", None)
    if client is None or task_uid is None:
        return
    client.wait_for_task(task_uid, timeout_in_ms=cfg.search.meilisearch_task_timeout_ms)


def _repo_aliases(repo: Repository) -> list[str]:
    haystack = f"{repo.full_id} {repo.namespace} {repo.name} {repo.repo_type}".lower()
    aliases: list[str] = []
    for key, terms in _ALIAS_TERMS.items():
        if key in haystack or any(term.lower() in haystack for term in terms):
            aliases.append(key)
            aliases.extend(terms)
    if repo.repo_type == "model":
        aliases.extend(("模型", "model"))
    elif repo.repo_type == "dataset":
        aliases.extend(("数据集", "dataset"))
    elif repo.repo_type == "space":
        aliases.extend(("空间", "演示", "demo", "space"))
    return sorted({term for term in aliases if term})


def repo_document(repo: Repository) -> dict[str, Any]:
    created_ts = int(repo.created_at.timestamp()) if repo.created_at else 0
    return {
        "id": f"{repo.repo_type}:{repo.full_id}",
        "repo_db_id": repo.id,
        "full_id": repo.full_id,
        "repo_type": repo.repo_type,
        "namespace": repo.namespace,
        "name": repo.name,
        "private": bool(repo.private),
        "downloads": int(repo.downloads or 0),
        "likes": int(repo.likes_count or 0),
        "created_at": repo.created_at.isoformat() if repo.created_at else None,
        "created_at_ts": created_ts,
        "aliases": _repo_aliases(repo),
    }


def ensure_repository_index() -> bool:
    """Create repository index settings if Meilisearch is available."""
    global _settings_initialized
    client = get_client()
    if client is None:
        return False
    index = client.index(REPOSITORY_INDEX)
    if _settings_initialized:
        return True

    try:
        try:
            wait_for_task(client.create_index(REPOSITORY_INDEX, {"primaryKey": "id"}))
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise
        wait_for_task(index.update_searchable_attributes([
            "full_id",
            "name",
            "namespace",
            "repo_type",
            "aliases",
        ]))
        wait_for_task(index.update_filterable_attributes([
            "repo_type",
            "private",
            "namespace",
        ]))
        wait_for_task(index.update_sortable_attributes([
            "downloads",
            "likes",
            "created_at_ts",
        ]))
        wait_for_task(index.update_ranking_rules([
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
            "downloads:desc",
            "likes:desc",
        ]))
        _settings_initialized = True
        return True
    except Exception as exc:
        logger.warning(f"Meilisearch index setup failed: {exc}")
        return False


def upsert_repository(repo: Repository) -> bool:
    """Add or update a repository document. Returns False on silent fallback."""
    index = get_index()
    if index is None:
        return False
    try:
        ensure_repository_index()
        wait_for_task(index.add_documents([repo_document(repo)], primary_key="id"))
        return True
    except Exception as exc:
        logger.warning(f"Meilisearch upsert failed for {repo.repo_type}:{repo.full_id}: {exc}")
        return False


def delete_repository(repo_type: str, full_id: str) -> bool:
    index = get_index()
    if index is None:
        return False
    try:
        wait_for_task(index.delete_document(f"{repo_type}:{full_id}"))
        return True
    except Exception as exc:
        logger.warning(f"Meilisearch delete failed for {repo_type}:{full_id}: {exc}")
        return False


def rebuild_repository_index() -> dict[str, Any]:
    """Rebuild all repository documents from the database."""
    index = get_index()
    if index is None:
        return {"enabled": is_enabled(), "available": False, "indexed": 0}

    started_at = time.time()
    documents = [repo_document(repo) for repo in Repository.select()]
    try:
        ensure_repository_index()
        wait_for_task(index.delete_all_documents())
        if documents:
            wait_for_task(index.add_documents(documents, primary_key="id"))
        return {
            "enabled": True,
            "available": True,
            "indexed": len(documents),
            "durationSeconds": round(time.time() - started_at, 3),
        }
    except Exception as exc:
        logger.warning(f"Meilisearch rebuild failed: {exc}")
        return {
            "enabled": True,
            "available": False,
            "indexed": 0,
            "error": str(exc),
        }


def search_repositories(
    query: str,
    *,
    repo_type: str | None,
    limit: int,
    sort: str,
) -> dict[str, Any] | None:
    """Search repositories with Meilisearch, returning None when unavailable."""
    index = get_index()
    if index is None:
        return None
    try:
        ensure_repository_index()
        filter_parts = []
        if repo_type and repo_type != "all":
            filter_parts.append(f'repo_type = "{repo_type}"')
        search_params: dict[str, Any] = {
            "limit": min(limit * 8, 500),
            "attributesToRetrieve": [
                "id",
                "repo_db_id",
                "full_id",
                "repo_type",
                "namespace",
                "name",
                "private",
                "downloads",
                "likes",
                "created_at",
                "aliases",
            ],
            "showRankingScore": True,
        }
        if filter_parts:
            search_params["filter"] = " AND ".join(filter_parts)
        if sort == "downloads":
            search_params["sort"] = ["downloads:desc"]
        elif sort == "likes":
            search_params["sort"] = ["likes:desc"]
        elif sort == "recent":
            search_params["sort"] = ["created_at_ts:desc"]

        return index.search(query, search_params)
    except Exception as exc:
        logger.warning(f"Meilisearch query failed; falling back to database search: {exc}")
        return None


def status() -> dict[str, Any]:
    index = get_index()
    if index is None:
        return {
            "enabled": is_enabled(),
            "available": False,
            "url": cfg.search.meilisearch_url,
            "index": REPOSITORY_INDEX,
        }
    try:
        stats = index.get_stats()
        return {
            "enabled": True,
            "available": True,
            "url": cfg.search.meilisearch_url,
            "index": REPOSITORY_INDEX,
            "numberOfDocuments": stats.get("numberOfDocuments"),
            "isIndexing": stats.get("isIndexing"),
        }
    except Exception as exc:
        return {
            "enabled": True,
            "available": False,
            "url": cfg.search.meilisearch_url,
            "index": REPOSITORY_INDEX,
            "error": str(exc),
        }
