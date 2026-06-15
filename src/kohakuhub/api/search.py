"""Public search API for repositories and namespaces."""

from __future__ import annotations

import operator
import re
import unicodedata
from functools import reduce
from typing import Iterable

from fastapi import APIRouter, Depends, Query

from kohakuhub.api.admin.utils import verify_admin_token
from kohakuhub.auth.dependencies import get_optional_user
from kohakuhub.auth.permissions import RepoReadDeniedError, check_repo_read_permission
from kohakuhub.db import Repository, User
from kohakuhub import search_index

router = APIRouter()

_LATIN_TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]*")
_CJK_RE = re.compile(r"[\u3400-\u9fff]")

_SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
    "千问": ("qwen", "通义", "通义千问", "tongyi"),
    "通义": ("qwen", "千问", "tongyi"),
    "通义千问": ("qwen", "千问", "tongyi"),
    "qwen": ("千问", "通义", "通义千问", "tongyi"),
    "智谱": ("glm", "chatglm", "zhipu", "清言"),
    "清言": ("glm", "chatglm", "zhipu", "智谱"),
    "glm": ("智谱", "清言", "chatglm", "zhipu"),
    "chatglm": ("智谱", "清言", "glm", "zhipu"),
    "百川": ("baichuan",),
    "baichuan": ("百川",),
    "书生": ("internlm", "浦语"),
    "浦语": ("internlm", "书生"),
    "internlm": ("书生", "浦语"),
    "混元": ("hunyuan",),
    "hunyuan": ("混元",),
    "文心": ("ernie", "wenxin"),
    "ernie": ("文心", "wenxin"),
    "kimi": ("moonshot", "月之暗面"),
    "月之暗面": ("kimi", "moonshot"),
    "零一万物": ("yi", "01-ai", "01ai"),
    "yi": ("零一万物", "01-ai", "01ai"),
    "deepseek": ("深度求索", "深度搜索"),
    "深度求索": ("deepseek",),
    "中文": ("chinese", "zh", "汉语"),
    "汉语": ("chinese", "zh", "中文"),
    "对话": ("chat", "chatbot", "聊天", "指令"),
    "聊天": ("chat", "chatbot", "对话", "指令"),
    "指令": ("instruct", "instruction", "chat", "对话"),
    "嵌入": ("embedding", "embeddings", "向量"),
    "向量": ("embedding", "embeddings", "嵌入"),
    "重排": ("rerank", "reranker"),
    "多模态": ("vlm", "vision", "视觉", "图像"),
    "视觉": ("vlm", "vision", "多模态", "图像"),
    "图像": ("vlm", "vision", "多模态", "视觉"),
}

_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "模型": ("model",),
    "model": ("模型",),
    "数据集": ("dataset",),
    "dataset": ("数据集",),
    "空间": ("space", "demo", "演示"),
    "space": ("空间", "demo", "演示"),
    "demo": ("space", "空间", "演示"),
}


def _normalize_text(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[\s_/.-]+", "", normalized)


def _dedupe_terms(terms: Iterable[str], *, limit: int = 28) -> list[str]:
    seen = set()
    result = []
    for term in terms:
        cleaned = unicodedata.normalize("NFKC", term.strip()).lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def _cjk_ngrams(text: str) -> list[str]:
    chars = [char for char in text if _CJK_RE.match(char)]
    if not chars:
        return []
    words = ["".join(chars)]
    words.extend(chars)
    words.extend("".join(chars[index : index + 2]) for index in range(len(chars) - 1))
    return words


def expand_query_terms(query: str) -> list[str]:
    """Return Chinese-aware search terms plus common model-family aliases."""
    base_terms = [query]
    base_terms.extend(_LATIN_TOKEN_RE.findall(query))
    base_terms.extend(_cjk_ngrams(query))

    expanded = []
    for term in _dedupe_terms(base_terms, limit=18):
        expanded.append(term)
        normalized_term = _normalize_text(term)
        for alias_key, aliases in {**_SEARCH_ALIASES, **_TYPE_ALIASES}.items():
            normalized_key = _normalize_text(alias_key)
            if normalized_term == normalized_key or normalized_key in normalized_term:
                expanded.extend(aliases)
                continue
            if any(_normalize_text(alias) in normalized_term for alias in aliases):
                expanded.append(alias_key)
                expanded.extend(aliases)

    return _dedupe_terms(expanded)


def _score_repo(repo: Repository, query: str, terms: list[str]) -> tuple[float, list[str]]:
    query_norm = _normalize_text(query)
    full_id_norm = _normalize_text(repo.full_id)
    name_norm = _normalize_text(repo.name)
    namespace_norm = _normalize_text(repo.namespace)
    type_norm = _normalize_text(repo.repo_type)

    score = 0.0
    matched_terms: list[str] = []

    if query_norm:
        if query_norm == full_id_norm:
            score += 140
        if query_norm == name_norm:
            score += 120
        if name_norm.startswith(query_norm):
            score += 72
        if full_id_norm.startswith(query_norm):
            score += 54
        if query_norm in name_norm:
            score += 46
        if query_norm in full_id_norm:
            score += 36
        if query_norm in namespace_norm:
            score += 18

    for term in terms:
        term_norm = _normalize_text(term)
        if not term_norm:
            continue
        term_matched = False
        if term_norm == name_norm:
            score += 42
            term_matched = True
        elif term_norm in name_norm:
            score += 24
            term_matched = True
        if term_norm in full_id_norm:
            score += 18
            term_matched = True
        if term_norm in namespace_norm:
            score += 9
            term_matched = True
        if term_norm == type_norm:
            score += 8
            term_matched = True
        if term_matched:
            matched_terms.append(term)

    score += min(repo.downloads or 0, 50000) / 10000
    score += min(repo.likes_count or 0, 5000) / 250
    return score, _dedupe_terms(matched_terms, limit=10)


def _repo_to_search_result(
    repo: Repository,
    *,
    score: float | None = None,
    matched_terms: list[str] | None = None,
) -> dict:
    return {
        "id": repo.full_id,
        "type": repo.repo_type,
        "author": repo.namespace,
        "name": repo.name,
        "private": repo.private,
        "downloads": repo.downloads,
        "likes": repo.likes_count,
        "createdAt": repo.created_at.isoformat() if repo.created_at else None,
        "score": round(score, 3) if score is not None else None,
        "matchedTerms": matched_terms or [],
    }


def _search_repositories_with_database(
    *,
    query: str,
    search_terms: list[str],
    repo_type: str | None,
    limit: int,
    sort: str,
    user: User | None,
) -> list[dict]:
    repo_conditions = []
    for term in search_terms:
        repo_conditions.extend(
            [
                Repository.full_id.contains(term),
                Repository.name.contains(term),
                Repository.namespace.contains(term),
                Repository.repo_type.contains(term),
            ]
        )

    repos_query = Repository.select()
    if repo_conditions:
        repos_query = repos_query.where(reduce(operator.or_, repo_conditions))

    if repo_type and repo_type != "all":
        repos_query = repos_query.where(Repository.repo_type == repo_type)

    if sort == "downloads":
        repos_query = repos_query.order_by(Repository.downloads.desc())
    elif sort == "likes":
        repos_query = repos_query.order_by(Repository.likes_count.desc())
    elif sort == "recent":
        repos_query = repos_query.order_by(Repository.created_at.desc())
    else:
        repos_query = repos_query.order_by(Repository.created_at.desc())

    candidates = []
    for repo in repos_query.limit(min(limit * 8, 500)):
        try:
            check_repo_read_permission(repo, user)
        except RepoReadDeniedError:
            continue
        relevance_score, matched_terms = _score_repo(repo, query, search_terms)
        if relevance_score > 0:
            candidates.append((repo, relevance_score, matched_terms))

    if sort == "downloads":
        candidates.sort(key=lambda item: (item[0].downloads or 0, item[1]), reverse=True)
    elif sort == "likes":
        candidates.sort(key=lambda item: (item[0].likes_count or 0, item[1]), reverse=True)
    elif sort == "recent":
        candidates.sort(
            key=lambda item: (item[0].created_at, item[1]),
            reverse=True,
        )
    else:
        candidates.sort(key=lambda item: item[1], reverse=True)

    return [
        _repo_to_search_result(repo, score=score, matched_terms=matched_terms)
        for repo, score, matched_terms in candidates[:limit]
    ]


def _search_repositories_with_meilisearch(
    *,
    query: str,
    search_terms: list[str],
    repo_type: str | None,
    limit: int,
    sort: str,
    user: User | None,
) -> list[dict] | None:
    meili_result = search_index.search_repositories(
        " ".join(search_terms) or query,
        repo_type=repo_type,
        limit=limit,
        sort=sort,
    )
    if meili_result is None:
        return None

    repositories = []
    for hit in meili_result.get("hits", []):
        repo = Repository.get_or_none(Repository.id == hit.get("repo_db_id"))
        if repo is None:
            search_index.delete_repository(hit.get("repo_type", ""), hit.get("full_id", ""))
            continue
        try:
            check_repo_read_permission(repo, user)
        except RepoReadDeniedError:
            continue
        score = hit.get("_rankingScore")
        if score is None:
            score, _ = _score_repo(repo, query, search_terms)
        aliases = hit.get("aliases") or []
        matched_terms = [
            term
            for term in search_terms
            if _normalize_text(term) in _normalize_text(" ".join(aliases))
            or _normalize_text(term) in _normalize_text(repo.full_id)
        ]
        repositories.append(
            _repo_to_search_result(
                repo,
                score=float(score),
                matched_terms=_dedupe_terms(matched_terms, limit=10),
            )
        )
        if len(repositories) >= limit:
            break
    return repositories


def _search_users(search_terms: list[str], limit: int) -> list[dict]:
    user_conditions = []
    for term in search_terms:
        user_conditions.extend(
            [
                User.username.contains(term),
                User.full_name.contains(term),
                User.description.contains(term),
                User.bio.contains(term),
            ]
        )
    user_query = (
        User.select()
        .where(reduce(operator.or_, user_conditions))
        .order_by(User.created_at.desc())
        .limit(min(limit, 20))
    )
    return [
        {
            "username": item.username,
            "name": item.full_name or item.username,
            "is_org": item.is_org,
            "bio": item.bio or item.description,
        }
        for item in user_query
    ]


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    repo_type: str | None = Query(
        None, pattern="^(model|dataset|space|all)$"
    ),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("relevance", pattern="^(relevance|recent|downloads|likes)$"),
    include_users: bool = Query(True),
    user: User | None = Depends(get_optional_user),
):
    """Search visible repositories and public namespaces."""
    query = q.strip()
    if not query:
        return {"query": q, "repositories": [], "users": []}

    search_terms = expand_query_terms(query)
    search_backend = "database"
    repositories = _search_repositories_with_meilisearch(
        query=query,
        search_terms=search_terms,
        repo_type=repo_type,
        limit=limit,
        sort=sort,
        user=user,
    )
    if repositories is not None:
        search_backend = "meilisearch"
    else:
        repositories = _search_repositories_with_database(
            query=query,
            search_terms=search_terms,
            repo_type=repo_type,
            limit=limit,
            sort=sort,
            user=user,
        )

    users = []
    if include_users:
        users = _search_users(search_terms, limit)

    return {
        "query": query,
        "terms": search_terms,
        "backend": search_backend,
        "repositories": repositories,
        "users": users,
    }


@router.get("/search/index/status")
async def search_index_status():
    return search_index.status()


@router.post("/search/index/rebuild")
async def rebuild_search_index(_admin: bool = Depends(verify_admin_token)):
    return search_index.rebuild_repository_index()
