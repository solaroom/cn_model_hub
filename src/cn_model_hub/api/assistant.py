"""Smart assistant API for platform Q&A and repository discovery."""

from __future__ import annotations

import asyncio
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from cn_model_hub.api import search as public_search
from cn_model_hub.auth.dependencies import get_optional_user
from cn_model_hub.auth.permissions import RepoReadDeniedError, check_repo_read_permission
from cn_model_hub.config import cfg
from cn_model_hub.db import File, Repository, User
from cn_model_hub.logger import get_logger
from cn_model_hub.utils.lakefs import get_lakefs_client, lakefs_repo_name

router = APIRouter()
logger = get_logger("ASSISTANT")

Intent = Literal["platform_qa", "repository_search", "combined"]

_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_LATIN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._+-]*")
_READMES = ("README.md", "readme.md", "Readme.md")
_README_CACHE: dict[tuple[str, str], str] = {}
_KNOWLEDGE_DIR = Path("docs/platform-knowledge")


@dataclass(frozen=True)
class KnowledgeChunk:
    title: str
    source: str
    url: str | None
    content: str
    priority: float = 0.0


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=4000)


class AssistantChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: list[AssistantMessage] = Field(default_factory=list, max_length=10)
    limit: int = Field(default=6, ge=1, le=10)


class AssistantChatResponse(BaseModel):
    question: str
    intent: Intent
    answer: str
    rag: dict[str, Any]
    search: dict[str, Any]
    llm: dict[str, Any]


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"\s+", " ", text).strip()


def _compact(value: object) -> str:
    return re.sub(r"[\s_/.-]+", "", _normalize(value))


def _tokens(text: str) -> set[str]:
    normalized = _normalize(text)
    tokens = set(_LATIN_RE.findall(normalized))
    cjk_chars = [char for char in normalized if _CJK_RE.match(char)]
    tokens.update(cjk_chars)
    tokens.update(
        "".join(cjk_chars[index : index + 2])
        for index in range(max(len(cjk_chars) - 1, 0))
    )
    return {token for token in tokens if token}


def _repo_url(repo_type: str, full_id: str) -> str:
    parts = full_id.split("/", 1)
    if len(parts) != 2:
        return f"/{quote(repo_type + 's', safe='')}/{quote(full_id, safe='')}"
    namespace, name = parts
    return (
        f"/{quote(repo_type + 's', safe='')}/"
        f"{quote(namespace, safe='')}/"
        f"{quote(name, safe='')}"
    )


def _repo_type_label(repo_type: str) -> str:
    return {"model": "模型", "dataset": "数据集", "space": "空间"}.get(
        repo_type, repo_type
    )


def _detect_intent(question: str) -> Intent:
    text = _normalize(question)
    search_words = (
        "找",
        "搜索",
        "推荐",
        "筛选",
        "有哪些",
        "有没有",
        "查一下",
        "参数量",
        "作者",
        "标签",
        "格式",
    )
    qa_words = (
        "怎么",
        "如何",
        "是什么",
        "什么意思",
        "解释",
        "介绍",
        "平台",
        "用",
        "mlflow",
        "lakefs",
        "评测",
        "demo",
        "space",
    )
    asks_search = any(word in text for word in search_words)
    asks_resource = "模型" in text or "数据集" in text or "model" in text or "dataset" in text
    asks_qa = any(word in text for word in qa_words)
    if asks_search and asks_qa:
        return "combined"
    if asks_search or (asks_resource and any(word in text for word in ("按", "筛", "找"))):
        return "repository_search"
    return "platform_qa"


def _requested_repo_types(question: str) -> list[str]:
    text = _normalize(question)
    wants_model = "模型" in text or "model" in text
    wants_dataset = "数据集" in text or "dataset" in text or "数据" in text
    if wants_model and wants_dataset:
        return ["model", "dataset"]
    if wants_dataset:
        return ["dataset"]
    if wants_model:
        return ["model"]
    return ["all"]


def _extract_filters(question: str) -> dict[str, Any]:
    text = _normalize(question)
    filters: dict[str, Any] = {
        "repo_types": _requested_repo_types(question),
        "tasks": [],
        "formats": [],
        "tags": [],
        "author": None,
        "parameter": None,
    }

    task_aliases = {
        "对话": ["对话", "聊天", "chat", "instruct", "指令"],
        "文本生成": ["文本生成", "生成", "text-generation", "causal-lm"],
        "嵌入": ["嵌入", "向量", "embedding", "sentence-similarity"],
        "重排": ["重排", "rerank", "reranker"],
        "多模态": ["多模态", "视觉", "图像", "vlm", "vision"],
        "评测": ["评测", "benchmark", "evaluation", "ceval", "c-eval"],
    }
    for label, aliases in task_aliases.items():
        if any(alias in text for alias in aliases):
            filters["tasks"].append(label)

    known_formats = [
        "safetensors",
        "gguf",
        "bin",
        "pt",
        "onnx",
        "parquet",
        "json",
        "jsonl",
        "csv",
        "arrow",
        "transformers",
        "gradio",
        "streamlit",
    ]
    filters["formats"] = [fmt for fmt in known_formats if fmt in text]

    author_match = re.search(r"(?:作者|用户|owner|author)\s*(?:是|为|:|：)?\s*([a-zA-Z0-9_.-]+)", text)
    if author_match:
        filters["author"] = author_match.group(1)

    parameter_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(b|m|亿|百万|千万|参数)?", text, re.IGNORECASE
    )
    if parameter_match and any(word in text for word in ("参数", "b", "亿", "百万")):
        filters["parameter"] = "".join(part or "" for part in parameter_match.groups())

    tag_match = re.search(r"(?:标签|tag)\s*(?:是|为|:|：)?\s*([\w\u3400-\u9fff,，、 -]+)", text)
    if tag_match:
        raw_tags = re.split(r"[,，、\s]+", tag_match.group(1))
        filters["tags"] = [tag for tag in raw_tags if tag]

    return filters


def _search_queries(question: str, filters: dict[str, Any]) -> list[str]:
    cleaned = question
    cleaned = re.sub(
        r"(帮我|请|搜索|查找|找一下|找|推荐|筛选|有哪些|有没有|平台上|平台里|一个|一些)",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"(模型|数据集|数据|作者|标签|格式|参数量|参数)", " ", cleaned)
    terms = []
    terms.extend(_LATIN_RE.findall(cleaned))
    terms.extend(re.findall(r"[\u3400-\u9fff]{2,}", cleaned))
    terms.extend(filters.get("tasks") or [])
    terms.extend(filters.get("formats") or [])
    if filters.get("parameter"):
        terms.append(str(filters["parameter"]))
    if filters.get("author"):
        terms.append(str(filters["author"]))
    terms.extend(filters.get("tags") or [])

    query = " ".join(term for term in terms if term).strip()
    queries = [question.strip()]
    if query:
        queries.append(query)
    if "千问" in question or "qwen" in question.lower():
        queries.append("qwen 千问")
    if "c-eval" in question.lower() or "ceval" in question.lower():
        queries.append("C-Eval")
    if not query:
        if filters.get("repo_types") == ["dataset"]:
            queries.append("数据集")
        elif filters.get("repo_types") == ["model"]:
            queries.append("模型")
        else:
            queries.append("中文")

    seen = set()
    deduped = []
    for item in queries:
        cleaned_item = _normalize(item)
        if cleaned_item and cleaned_item not in seen:
            seen.add(cleaned_item)
            deduped.append(item)
    return deduped[:4]


def _source_url(source: str) -> str | None:
    if source.startswith("docs/"):
        slug = source.removeprefix("docs/").removesuffix(".md")
        return f"/docs/{slug}"
    if source == "README.md":
        return "/"
    return None


def _knowledge_markdown_files() -> list[tuple[str, str]]:
    for root in _project_roots():
        base = root / _KNOWLEDGE_DIR
        if not base.exists():
            continue
        files: list[tuple[str, str]] = []
        for path in sorted(base.rglob("*.md")):
            relative = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            title = path.stem.replace("-", " ")
            for line in text.splitlines():
                heading = re.match(r"^#\s+(.+)$", line.strip())
                if heading:
                    title = heading.group(1).strip()
                    break
            files.append((relative, title))
        return files
    return []


def _project_roots() -> list[Path]:
    roots = [Path.cwd()]
    try:
        roots.append(Path(__file__).resolve().parents[3])
    except IndexError:
        pass
    seen = set()
    result = []
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        result.append(root)
    return result


def _read_text_file(relative_path: str) -> str:
    for root in _project_roots():
        path = root / relative_path
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :].lstrip()
    return text


def _split_markdown(relative_path: str, title: str, url: str | None) -> list[KnowledgeChunk]:
    text = _strip_frontmatter(_read_text_file(relative_path))
    if not text:
        return []
    chunks: list[KnowledgeChunk] = []
    current_title = title
    buffer: list[str] = []

    def flush() -> None:
        content = "\n".join(buffer).strip()
        if not content:
            return
        while len(content) > 1500:
            part = content[:1500]
            cut = max(part.rfind("\n"), part.rfind("。"), part.rfind("."))
            if cut < 500:
                cut = 1500
            chunks.append(
                KnowledgeChunk(
                    title=current_title,
                    source=relative_path,
                    url=url,
                    content=content[:cut].strip(),
                )
            )
            content = content[cut:].strip()
        if content:
            chunks.append(
                KnowledgeChunk(
                    title=current_title,
                    source=relative_path,
                    url=url,
                    content=content,
                )
            )

    for line in text.splitlines():
        heading = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if heading:
            flush()
            buffer = []
            current_title = heading.group(2).strip()
        else:
            buffer.append(line)
    flush()
    return chunks


class KnowledgeIndex:
    def __init__(self) -> None:
        self._chunks: list[KnowledgeChunk] | None = None
        self._embedder: Any | None = None
        self._embeddings: Any | None = None
        self._embedding_error: str | None = None

    def chunks(self) -> list[KnowledgeChunk]:
        if self._chunks is not None:
            return self._chunks

        files = _knowledge_markdown_files()
        chunks: list[KnowledgeChunk] = []
        for relative_path, title in files:
            chunks.extend(
                _split_markdown(relative_path, title, _source_url(relative_path))
            )
        if not chunks:
            chunks.append(
                KnowledgeChunk(
                    title="平台知识库未配置",
                    source=_KNOWLEDGE_DIR.as_posix(),
                    url="/docs/platform-knowledge",
                    content=(
                        "当前没有可索引的中文平台知识文档。请在 "
                        "docs/platform-knowledge/ 下添加 Markdown 文件。"
                    ),
                )
            )
        self._chunks = chunks
        return chunks

    def _load_embedder(self) -> Any | None:
        if not cfg.assistant.embedding_enabled:
            self._embedding_error = "embedding disabled"
            return None
        if self._embedder is not None:
            return self._embedder
        if self._embedding_error is not None:
            return None
        try:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer(cfg.assistant.embedding_model)
            return self._embedder
        except Exception as exc:
            self._embedding_error = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "Assistant embedding model unavailable; falling back to lexical RAG: "
                f"{type(exc).__name__}: {exc}"
            )
            return None

    async def search(self, query: str, limit: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        chunks = self.chunks()
        embedder = self._load_embedder()
        if embedder is not None:
            return await self._semantic_search(query, chunks, embedder, limit)
        return self._lexical_search(query, chunks, limit)

    async def _semantic_search(
        self,
        query: str,
        chunks: list[KnowledgeChunk],
        embedder: Any,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        try:
            import numpy as np

            if self._embeddings is None:
                contents = [chunk.content for chunk in chunks]
                self._embeddings = await asyncio.to_thread(
                    embedder.encode,
                    contents,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
            query_vector = await asyncio.to_thread(
                embedder.encode,
                [query],
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            scores = np.matmul(self._embeddings, query_vector[0])
            ranked = sorted(
                enumerate(scores.tolist()), key=lambda item: item[1], reverse=True
            )[:limit]
            return (
                [self._serialize_chunk(chunks[index], float(score)) for index, score in ranked],
                {
                    "mode": "semantic",
                    "embedding_model": cfg.assistant.embedding_model,
                    "chunk_count": len(chunks),
                },
            )
        except Exception as exc:
            self._embedding_error = f"{type(exc).__name__}: {exc}"
            logger.warning(f"Assistant semantic RAG failed; using lexical RAG: {exc}")
            return self._lexical_search(query, chunks, limit)

    def _lexical_search(
        self, query: str, chunks: list[KnowledgeChunk], limit: int
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        query_tokens = _tokens(query)
        query_text = _normalize(query)
        query_compact = _compact(query)
        development_terms = (
            "启动",
            "开发",
            "docker",
            "端口",
            "报错",
            "错误",
            "本地",
            "安装",
            "配置",
            "服务",
        )
        ranked = []
        for chunk in chunks:
            haystack = f"{chunk.title} {chunk.content}"
            title_text = _normalize(chunk.title)
            chunk_tokens = _tokens(haystack)
            overlap = len(query_tokens & chunk_tokens)
            score = overlap / max(math.sqrt(len(chunk_tokens) or 1), 1)
            score += chunk.priority
            for token in query_tokens:
                if len(token) > 1 and token in title_text:
                    score += 4
            if chunk.source.startswith("docs/development/") and not any(
                term in query_text for term in development_terms
            ):
                score -= 3
            if query_compact and query_compact in _compact(haystack):
                score += 3
            if score > 0:
                ranked.append((chunk, score))
        ranked.sort(key=lambda item: item[1], reverse=True)
        if not ranked:
            ranked = [(chunk, 0.1) for chunk in chunks[:limit]]
        return (
            [self._serialize_chunk(chunk, score) for chunk, score in ranked[:limit]],
            {
                "mode": "lexical",
                "embedding_model": cfg.assistant.embedding_model,
                "embedding_error": self._embedding_error,
                "chunk_count": len(chunks),
            },
        )

    @staticmethod
    def _serialize_chunk(chunk: KnowledgeChunk, score: float) -> dict[str, Any]:
        return {
            "title": chunk.title,
            "source": chunk.source,
            "url": chunk.url,
            "score": round(float(score), 4),
            "excerpt": chunk.content[:700],
        }


_knowledge_index = KnowledgeIndex()


async def _read_repo_readme(repo: Repository) -> str:
    key = (repo.repo_type, repo.full_id)
    if key in _README_CACHE:
        return _README_CACHE[key]
    client = get_lakefs_client()
    lakefs_repo = lakefs_repo_name(repo.repo_type, repo.full_id)
    for readme in _READMES:
        try:
            content = await client.get_object(
                repository=lakefs_repo, ref="main", path=readme
            )
            text = content.decode("utf-8", errors="ignore")
            _README_CACHE[key] = text[:12000]
            return _README_CACHE[key]
        except Exception:
            continue
    _README_CACHE[key] = ""
    return ""


async def _repo_haystack(repo: Repository) -> str:
    file_paths = [
        file.path_in_repo
        for file in File.select()
        .where((File.repository == repo) & (File.is_deleted == False))  # noqa: E712
        .limit(120)
    ]
    readme = await _read_repo_readme(repo)
    return " ".join(
        [
            repo.full_id,
            repo.namespace,
            repo.name,
            repo.repo_type,
            " ".join(file_paths),
            readme,
        ]
    )


def _matches_text_filter(haystack: str, values: list[str]) -> bool:
    if not values:
        return True
    compact_haystack = _compact(haystack)
    return any(_compact(value) in compact_haystack for value in values)


def _parameter_matches(haystack: str, parameter: str | None) -> bool:
    if not parameter:
        return True
    text = _compact(haystack)
    param = _compact(parameter)
    if param in text:
        return True
    numeric = re.search(r"\d+(?:\.\d+)?", param)
    if not numeric:
        return True
    value = numeric.group(0)
    return value in text


async def _serialize_search_result(
    raw: dict[str, Any], filters: dict[str, Any]
) -> tuple[dict[str, Any] | None, bool]:
    repo = Repository.get_or_none(
        (Repository.full_id == raw.get("id")) & (Repository.repo_type == raw.get("type"))
    )
    if repo is None:
        return None, False
    haystack = await _repo_haystack(repo)

    matches = True
    matched_filters: list[str] = []
    if filters.get("author"):
        matches = matches and _compact(filters["author"]) in _compact(repo.namespace)
        if matches:
            matched_filters.append(f"作者: {repo.namespace}")
    if filters.get("formats"):
        format_match = _matches_text_filter(haystack, filters["formats"])
        matches = matches and format_match
        if format_match:
            matched_filters.append("格式")
    if filters.get("tasks"):
        task_match = _matches_text_filter(haystack, filters["tasks"])
        matches = matches and task_match
        if task_match:
            matched_filters.append("任务")
    if filters.get("tags"):
        tag_match = _matches_text_filter(haystack, filters["tags"])
        matches = matches and tag_match
        if tag_match:
            matched_filters.append("标签")
    if filters.get("parameter"):
        parameter_match = _parameter_matches(haystack, filters["parameter"])
        matches = matches and parameter_match
        if parameter_match:
            matched_filters.append("参数量")

    file_formats = []
    for file in File.select().where((File.repository == repo) & (File.is_deleted == False)).limit(60):  # noqa: E501,E712
        suffix = Path(file.path_in_repo).suffix.lower().lstrip(".")
        if suffix and suffix not in file_formats:
            file_formats.append(suffix)

    title = repo.name if repo.repo_type == "dataset" else repo.full_id

    return (
        {
            "id": repo.full_id,
            "title": title,
            "type": repo.repo_type,
            "type_label": _repo_type_label(repo.repo_type),
            "author": repo.namespace,
            "name": repo.name,
            "url": _repo_url(repo.repo_type, repo.full_id),
            "downloads": repo.downloads,
            "likes": repo.likes_count,
            "matched_terms": raw.get("matchedTerms") or [],
            "matched_filters": matched_filters,
            "formats": file_formats[:8],
            "score": raw.get("score"),
        },
        matches,
    )


async def _fallback_repository_pool(
    repo_type: str | None, user: User | None, limit: int
) -> list[dict[str, Any]]:
    query = Repository.select().order_by(Repository.created_at.desc())
    if repo_type and repo_type != "all":
        query = query.where(Repository.repo_type == repo_type)
    results = []
    for repo in query.limit(min(limit, 100)):
        try:
            check_repo_read_permission(repo, user)
        except RepoReadDeniedError:
            continue
        results.append(
            {
                "id": repo.full_id,
                "type": repo.repo_type,
                "author": repo.namespace,
                "name": repo.name,
                "score": 0,
                "matchedTerms": [],
            }
        )
    return results


async def _run_repository_search(
    question: str, filters: dict[str, Any], user: User | None, limit: int
) -> dict[str, Any]:
    queries = _search_queries(question, filters)
    repo_types = filters.get("repo_types") or ["all"]
    raw_results: list[dict[str, Any]] = []
    backends: list[str] = []
    seen: set[tuple[str, str]] = set()

    for repo_type in repo_types:
        for query in queries:
            response = await public_search.search(
                q=query,
                repo_type=None if repo_type == "all" else repo_type,
                limit=30,
                sort="relevance",
                include_users=False,
                user=user,
            )
            backends.append(response.get("backend", "unknown"))
            for item in response.get("repositories", []):
                key = (item.get("type"), item.get("id"))
                if key in seen:
                    continue
                seen.add(key)
                raw_results.append(item)

    if not raw_results:
        for repo_type in repo_types:
            raw_results.extend(await _fallback_repository_pool(repo_type, user, 30))

    exact_results: list[dict[str, Any]] = []
    relaxed_results: list[dict[str, Any]] = []
    for item in raw_results:
        serialized, matches = await _serialize_search_result(item, filters)
        if serialized is None:
            continue
        if matches:
            exact_results.append(serialized)
        relaxed_results.append(serialized)
        if len(exact_results) >= limit and len(relaxed_results) >= limit * 2:
            break

    relaxed = False
    results = exact_results[:limit]
    if not results:
        relaxed = True
        results = relaxed_results[:limit]

    return {
        "queries": queries,
        "filters": filters,
        "backend": "meilisearch" if "meilisearch" in backends else (backends[0] if backends else "database"),
        "relaxed": relaxed,
        "results": results,
    }


async def _call_llm(
    question: str,
    intent: Intent,
    rag_sources: list[dict[str, Any]],
    search_results: list[dict[str, Any]],
    history: list[AssistantMessage],
) -> tuple[str | None, dict[str, Any]]:
    api_key = cfg.assistant.llm_api_key
    if not api_key:
        return None, {
            "provider": "fallback",
            "model": cfg.assistant.llm_model,
            "error": "助手 LLM API Key 未配置",
        }

    source_text = "\n\n".join(
        f"[{index + 1}] {source['title']} ({source['source']})\n{source['excerpt']}"
        for index, source in enumerate(rag_sources)
    )
    result_text = "\n".join(
        f"- {item['title']} | {item['type_label']} | 站内链接 {item['url']} | 作者 {item['author']}"
        for item in search_results
    )
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "你是中文开源AI模型社区的站内智能助手。"
                "只根据给定的平台资料和搜索结果回答；不确定时要说明。"
                "回答必须包含可读的中文说明、真实本站链接，并在末尾列出来源。"
                "严禁编造或使用 Hugging Face、ModelScope、魔塔社区等外部资源链接；"
                "模型、数据集、Demo 的链接只能使用搜索结果中给出的站内链接。"
            ),
        }
    ]
    for item in history[-6:]:
        messages.append({"role": item.role, "content": item.content[:1200]})
    messages.append(
        {
            "role": "user",
            "content": (
                f"用户问题：{question}\n"
                f"Agent 判断意图：{intent}\n\n"
                f"平台知识片段：\n{source_text or '无'}\n\n"
                f"搜索结果：\n{result_text or '无'}\n\n"
                "请整理最终答案。若有搜索结果，用 Markdown 链接列出。"
                "若引用平台知识，请用“来源：标题（路径）”列出。"
            ),
        }
    )
    base_url = cfg.assistant.llm_base_url
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": cfg.assistant.llm_model,
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=cfg.assistant.llm_timeout_seconds) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        return answer, {
            "provider": cfg.assistant.llm_provider,
            "model": cfg.assistant.llm_model,
            "base_url": base_url,
        }
    except Exception as exc:
        logger.warning(
            f"Assistant LLM call failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return None, {
            "provider": "fallback",
            "model": cfg.assistant.llm_model,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _enforce_platform_links(answer: str, search_results: list[dict[str, Any]]) -> str:
    external_resource_link = re.compile(
        r"\[([^\]]+)\]\((https?://(?:www\.)?(?:modelscope\.cn|huggingface\.co|hf\.co)[^)]+)\)",
        re.IGNORECASE,
    )
    answer = external_resource_link.sub(r"\1", answer)
    answer = re.sub(
        r"https?://(?:www\.)?(?:modelscope\.cn|huggingface\.co|hf\.co)\S*",
        "",
        answer,
        flags=re.IGNORECASE,
    )

    if not search_results:
        return answer.strip()

    missing_results = [
        item for item in search_results if str(item.get("url") or "") not in answer
    ]
    if not missing_results:
        return answer.strip()

    lines = ["", "站内可点击结果："]
    for item in missing_results[:6]:
        lines.append(
            f"- [{item['title']}]({item['url']}) · {item['type_label']} · 作者 {item['author']}"
        )
    return (answer.rstrip() + "\n".join(lines)).strip()


def _fallback_answer(
    question: str,
    intent: Intent,
    sources: list[dict[str, Any]],
    search_data: dict[str, Any],
    llm_state: dict[str, Any],
) -> str:
    lines = [f"我先按“{intent}”处理你的问题。"]
    results = search_data.get("results") or []
    if results:
        if search_data.get("relaxed"):
            lines.append("没有找到完全匹配筛选条件的资源，下面是最接近的真实平台结果：")
        else:
            lines.append("找到这些真实平台资源：")
        for item in results:
            meta = []
            if item.get("formats"):
                meta.append("格式：" + "、".join(item["formats"][:4]))
            if item.get("matched_filters"):
                meta.append("匹配：" + "、".join(item["matched_filters"]))
            suffix = f"（{'；'.join(meta)}）" if meta else ""
            lines.append(f"- [{item['title']}]({item['url']}) · {item['type_label']} · 作者 {item['author']}{suffix}")

    if intent in ("platform_qa", "combined"):
        lines.append("")
        lines.append("平台用法要点：")
        for source in sources[:4]:
            excerpt = re.sub(r"\s+", " ", source.get("excerpt", "")).strip()
            if len(excerpt) > 180:
                excerpt = excerpt[:180].rstrip() + "..."
            lines.append(f"- {source['title']}：{excerpt}")

    if llm_state.get("error"):
        lines.append("")
        lines.append("当前大模型整理未启用或调用失败，以上为平台检索结果的本地整理。")

    if sources:
        lines.append("")
        lines.append("来源：")
        for source in sources[:5]:
            source_label = source["source"]
            if source.get("url"):
                lines.append(f"- [{source['title']}]({source['url']})（{source_label}）")
            else:
                lines.append(f"- {source['title']}（{source_label}）")
    return "\n".join(lines)


@router.get("/assistant/status")
async def assistant_status():
    chunks = _knowledge_index.chunks()
    return {
        "llm_provider": cfg.assistant.llm_provider,
        "llm_model": cfg.assistant.llm_model,
        "llm_configured": bool(cfg.assistant.llm_api_key),
        "embedding_model": cfg.assistant.embedding_model,
        "embedding_enabled": cfg.assistant.embedding_enabled,
        "knowledge_directory": _KNOWLEDGE_DIR.as_posix(),
        "knowledge_chunks": len(chunks),
    }


@router.post("/assistant/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    payload: AssistantChatRequest,
    user: User | None = Depends(get_optional_user),
):
    question = payload.question.strip()
    intent = _detect_intent(question)
    filters = _extract_filters(question)

    sources: list[dict[str, Any]] = []
    rag_meta: dict[str, Any] = {}
    if intent in ("platform_qa", "combined"):
        sources, rag_meta = await _knowledge_index.search(
            question, min(cfg.assistant.max_knowledge_chunks, 8)
        )
    else:
        rag_meta = {
            "mode": "skipped",
            "embedding_model": cfg.assistant.embedding_model,
            "chunk_count": len(_knowledge_index.chunks()),
        }

    search_data: dict[str, Any] = {
        "queries": [],
        "filters": filters,
        "backend": None,
        "relaxed": False,
        "results": [],
    }
    if intent in ("repository_search", "combined"):
        search_data = await _run_repository_search(
            question, filters, user, payload.limit
        )

    llm_answer, llm_state = await _call_llm(
        question,
        intent,
        sources,
        search_data.get("results") or [],
        payload.history,
    )
    answer = llm_answer or _fallback_answer(
        question, intent, sources, search_data, llm_state
    )
    answer = _enforce_platform_links(answer, search_data.get("results") or [])

    return AssistantChatResponse(
        question=question,
        intent=intent,
        answer=answer,
        rag={**rag_meta, "sources": sources},
        search=search_data,
        llm=llm_state,
    )
