"""Local Qwen2.5 chat demo for cn_model_hub model repositories."""

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
