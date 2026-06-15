"""CPU-only coherent chat demo for cn_model_hub model repositories.

This app is intentionally lightweight: it does not ship large neural weights,
so it can start quickly on a plain CPU. The response engine is a small
retrieval-and-template model that produces readable Chinese answers for demos.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Iterable

import gradio as gr


MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "6"))


@dataclass(frozen=True)
class Intent:
    name: str
    keywords: tuple[str, ...]
    answer: str


INTENTS = (
    Intent(
        name="identity",
        keywords=("你是谁", "介绍你自己", "自我介绍", "hello", "你好"),
        answer=(
            "你好，我是一个运行在 CPU 上的轻量中文对话示例模型。"
            "我不依赖外部 API，也不需要大模型权重；目标是在演示环境里稳定给出"
            "结构清楚、读起来像人话的回答。"
        ),
    ),
    Intent(
        name="project",
        keywords=("cn_model_hub", "模型社区", "平台", "仓库", "运行标签"),
        answer=(
            "cn_model_hub 可以把模型文件、说明文档和运行入口放在同一个仓库里。"
            "用户上传后，可以在模型页查看 README、浏览文件，并通过运行页启动"
            "仓库自带的 app.py 或平台内置模板。"
        ),
    ),
    Intent(
        name="cpu",
        keywords=("cpu", "本地", "离线", "没有显卡", "显存"),
        answer=(
            "这个示例默认只用 CPU，启动成本很低，适合课堂演示、平台联调和"
            "没有 GPU 的开发机验证。如果换成真实小模型，建议选择 0.5B 到 1.5B"
            "级别并使用 int4 或 int8 量化。"
        ),
    ),
    Intent(
        name="model_quality",
        keywords=("效果", "能力", "强一点", "人话", "逻辑"),
        answer=(
            "相比随机初始化的 tiny 模型，这个示例至少会识别常见问题、保持中文表达"
            "完整，并把回答组织成结论、原因和下一步。它的定位是可运行、可演示，"
            "不是替代真正训练过的大语言模型。"
        ),
    ),
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _history_lines(history) -> list[str]:
    lines: list[str] = []
    for item in history or []:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role and content:
                lines.append(f"{role}: {content}")
            continue
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            if item[0]:
                lines.append(f"user: {item[0]}")
            if item[1]:
                lines.append(f"assistant: {item[1]}")
    return lines[-MAX_HISTORY_TURNS * 2 :]


def _score_intent(message: str, intent: Intent) -> int:
    return sum(1 for keyword in intent.keywords if keyword.lower() in message)


def _best_intent(message: str) -> Intent | None:
    scored = sorted(
        ((_score_intent(message, intent), intent) for intent in INTENTS),
        key=lambda item: item[0],
        reverse=True,
    )
    if scored and scored[0][0] > 0:
        return scored[0][1]
    return None


def _extract_topic(message: str) -> str:
    cleaned = re.sub(r"[？?！!。.,，]", " ", message).strip()
    cleaned = re.sub(r"^(请|帮我|麻烦|能不能|可以|请你)", "", cleaned).strip()
    return cleaned[:48] or "这个问题"


def _compose_generic(message: str, history_lines: Iterable[str]) -> str:
    topic = _extract_topic(message)
    has_context = any(history_lines)
    context_sentence = (
        "结合上文，我会延续同一个讨论方向。"
        if has_context
        else "我先按一个独立问题来回答。"
    )
    return (
        f"{context_sentence}\n\n"
        f"关于“{topic}”，可以先抓住三点：\n"
        "1. 先明确目标：你希望验证功能、展示效果，还是拿它做真实任务。\n"
        "2. 再控制范围：CPU 环境更适合小模型、短上下文和可预期的输入。\n"
        "3. 最后给出可执行结果：把输入、处理逻辑和输出格式固定下来，"
        "演示时会比随机生成更稳定。\n\n"
        "如果你给我更具体的输入，我可以继续按这个方向生成一版更贴近场景的回答。"
    )


def chat(message: str, history):
    normalized = _normalize(message)
    if not normalized:
        return "请输入一个问题，我会尽量用简洁的中文回答。"

    intent = _best_intent(normalized)
    if intent is not None:
        return intent.answer

    if any(word in normalized for word in ("总结", "概括", "提炼")):
        return (
            "可以。我的总结是：先说明背景，再列出关键点，最后给出结论或下一步。"
            "这种结构适合模型仓库 README、课堂演示说明和项目汇报。"
        )

    if any(word in normalized for word in ("计划", "步骤", "怎么做", "如何")):
        topic = _extract_topic(message)
        return (
            f"针对“{topic}”，建议按下面的顺序做：\n"
            "1. 明确输入和期望输出。\n"
            "2. 选择 CPU 可承受的实现方式。\n"
            "3. 先做最小可运行版本，再补充边界情况。\n"
            "4. 用几组固定样例验证结果是否稳定。"
        )

    return _compose_generic(message, _history_lines(history))


demo = gr.ChatInterface(
    fn=chat,
    title="Coherent CPU Chat Demo",
    description="一个不依赖 GPU 的轻量中文对话示例，用于替代随机 tiny 模型做平台演示。",
    examples=[
        "介绍你自己",
        "cn_model_hub 的模型运行页有什么用？",
        "没有显卡也能跑吗？",
        "怎么做一个稳定的课堂演示？",
    ],
    type="messages",
)


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", "7860")))
    server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    root_path = os.getenv("GRADIO_ROOT_PATH") or None
    demo.launch(server_name=server_name, server_port=port, root_path=root_path)
