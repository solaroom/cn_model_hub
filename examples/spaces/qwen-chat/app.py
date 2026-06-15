"""Qwen chat Space template for cn_model_hub.

Required environment variable:
  DASHSCOPE_API_KEY or QWEN_API_KEY

Optional environment variables:
  QWEN_MODEL, QWEN_BASE_URL, QWEN_SYSTEM_PROMPT, PORT
"""

from __future__ import annotations

import os

import gradio as gr
from openai import OpenAI


QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")
QWEN_BASE_URL = os.getenv(
    "QWEN_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
SYSTEM_PROMPT = os.getenv(
    "QWEN_SYSTEM_PROMPT",
    "你是中文开源AI模型社区里的千问助手，请用简洁、准确的中文回答。",
)


def _api_key() -> str:
    return os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY") or ""


def _messages(message: str, history: list[dict] | list[tuple[str, str]]) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history or []:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
            continue

        if isinstance(item, (list, tuple)) and len(item) >= 2:
            user_text, assistant_text = item[0], item[1]
            if user_text:
                messages.append({"role": "user", "content": user_text})
            if assistant_text:
                messages.append({"role": "assistant", "content": assistant_text})

    messages.append({"role": "user", "content": message})
    return messages


def chat(message: str, history):
    key = _api_key()
    if not key:
        yield (
            "Space 已经启动，但还没有配置千问 API Key。\n\n"
            "请在运行环境里设置 `DASHSCOPE_API_KEY` 或 `QWEN_API_KEY`，"
            "然后重新启动 Space。"
        )
        return

    client = OpenAI(api_key=key, base_url=QWEN_BASE_URL)
    answer = ""
    try:
        stream = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=_messages(message, history),
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            answer += delta
            yield answer
    except Exception as exc:
        yield f"调用千问失败：{exc}"


demo = gr.ChatInterface(
    fn=chat,
    title="千问对话 Demo",
    description="基于 cn_model_hub Space 模板运行。配置 DASHSCOPE_API_KEY 后即可对话。",
    examples=["介绍一下中文开源AI模型社区", "给我一个中文大模型评测方案"],
    type="messages",
)


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", "7860")))
    server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    root_path = os.getenv("GRADIO_ROOT_PATH") or None
    demo.launch(server_name=server_name, server_port=port, root_path=root_path)
