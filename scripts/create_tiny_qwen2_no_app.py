"""Generate a tiny local Qwen2-style model repo without app.py.

The artifact is intentionally tiny and randomly initialized. It is only useful
for validating cn_model_hub's built-in "model repo without app.py" runtime path.
"""

from __future__ import annotations

import json
import random
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "models" / "tiny-qwen2-no-app"

VOCAB = {
    "<|endoftext|>": 0,
    "<|im_start|>": 1,
    "<|im_end|>": 2,
    "<unk>": 3,
    "system": 4,
    "user": 5,
    "assistant": 6,
    "hello": 7,
    "world": 8,
    "model": 9,
    "demo": 10,
    "中文": 11,
    "模型": 12,
    "运行": 13,
    "测试": 14,
    "。": 15,
}

for i in range(16, 64):
    VOCAB[f"tok{i}"] = i


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_values(count: int, scale: float = 0.02) -> bytes:
    return b"".join(struct.pack("<f", random.uniform(-scale, scale)) for _ in range(count))


def tensor_bytes(shape: list[int], scale: float = 0.02) -> bytes:
    count = 1
    for dim in shape:
        count *= dim
    return make_values(count, scale)


def write_safetensors(path: Path, tensors: dict[str, tuple[list[int], bytes]]) -> None:
    header: dict[str, dict] = {"__metadata__": {"format": "pt"}}
    offset = 0
    data_parts = []
    for name, (shape, raw) in tensors.items():
        header[name] = {
            "dtype": "F32",
            "shape": shape,
            "data_offsets": [offset, offset + len(raw)],
        }
        data_parts.append(raw)
        offset += len(raw)

    header_bytes = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    padding = (8 - (len(header_bytes) % 8)) % 8
    header_bytes += b" " * padding
    path.write_bytes(struct.pack("<Q", len(header_bytes)) + header_bytes + b"".join(data_parts))


def main() -> None:
    random.seed(20260615)
    OUT.mkdir(parents=True, exist_ok=True)

    config = {
        "architectures": ["Qwen2ForCausalLM"],
        "model_type": "qwen2",
        "vocab_size": 64,
        "hidden_size": 16,
        "intermediate_size": 32,
        "num_hidden_layers": 1,
        "num_attention_heads": 2,
        "num_key_value_heads": 2,
        "max_position_embeddings": 128,
        "rope_theta": 1000000.0,
        "rms_norm_eps": 1e-6,
        "attention_dropout": 0.0,
        "bos_token_id": 1,
        "eos_token_id": 2,
        "pad_token_id": 0,
        "tie_word_embeddings": False,
        "torch_dtype": "float32",
    }
    write_json(OUT / "config.json", config)

    write_json(
        OUT / "generation_config.json",
        {
            "bos_token_id": 1,
            "eos_token_id": 2,
            "pad_token_id": 0,
            "max_new_tokens": 32,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9,
            "transformers_version": "4.43.0",
        },
    )

    chat_template = (
        "{% for message in messages %}"
        "{{'<|im_start|>' + message['role'] + '\\n' + message['content'] + '<|im_end|>\\n'}}"
        "{% endfor %}"
        "{% if add_generation_prompt %}{{ '<|im_start|>assistant\\n' }}{% endif %}"
    )
    write_json(
        OUT / "tokenizer_config.json",
        {
            "tokenizer_class": "PreTrainedTokenizerFast",
            "unk_token": "<unk>",
            "bos_token": "<|im_start|>",
            "eos_token": "<|im_end|>",
            "pad_token": "<|endoftext|>",
            "chat_template": chat_template,
            "model_max_length": 128,
        },
    )
    write_json(
        OUT / "special_tokens_map.json",
        {
            "unk_token": "<unk>",
            "bos_token": "<|im_start|>",
            "eos_token": "<|im_end|>",
            "pad_token": "<|endoftext|>",
        },
    )
    tokenizer = {
        "version": "1.0",
        "truncation": None,
        "padding": None,
        "added_tokens": [
            {
                "id": token_id,
                "content": token,
                "single_word": False,
                "lstrip": False,
                "rstrip": False,
                "normalized": False,
                "special": token.startswith("<"),
            }
            for token, token_id in VOCAB.items()
            if token.startswith("<")
        ],
        "normalizer": None,
        "pre_tokenizer": {"type": "Whitespace"},
        "post_processor": None,
        "decoder": None,
        "model": {"type": "WordLevel", "vocab": VOCAB, "unk_token": "<unk>"},
    }
    write_json(OUT / "tokenizer.json", tokenizer)

    h = config["hidden_size"]
    i = config["intermediate_size"]
    vocab = config["vocab_size"]
    tensors: dict[str, tuple[list[int], bytes]] = {
        "model.embed_tokens.weight": ([vocab, h], tensor_bytes([vocab, h])),
        "model.layers.0.self_attn.q_proj.weight": ([h, h], tensor_bytes([h, h])),
        "model.layers.0.self_attn.k_proj.weight": ([h, h], tensor_bytes([h, h])),
        "model.layers.0.self_attn.v_proj.weight": ([h, h], tensor_bytes([h, h])),
        "model.layers.0.self_attn.o_proj.weight": ([h, h], tensor_bytes([h, h])),
        "model.layers.0.mlp.gate_proj.weight": ([i, h], tensor_bytes([i, h])),
        "model.layers.0.mlp.up_proj.weight": ([i, h], tensor_bytes([i, h])),
        "model.layers.0.mlp.down_proj.weight": ([h, i], tensor_bytes([h, i])),
        "model.layers.0.input_layernorm.weight": ([h], make_values(h, 0.0)),
        "model.layers.0.post_attention_layernorm.weight": ([h], make_values(h, 0.0)),
        "model.norm.weight": ([h], make_values(h, 0.0)),
        "lm_head.weight": ([vocab, h], tensor_bytes([vocab, h])),
    }
    write_safetensors(OUT / "model.safetensors", tensors)

    readme = """---
license: apache-2.0
language:
  - zh
library_name: transformers
pipeline_tag: text-generation
tags:
  - qwen2
  - tiny
  - no-app-py
  - local-runtime-test
cn_model:
  display_name: Tiny Qwen2 无 app.py 运行测试
  model_family: Qwen2
  model_type: causal-lm
  parameter_count: tiny-random
  tasks:
    - 运行链路验证
  recommended_use: 仅用于验证 cn_model_hub 模型仓库无 app.py 时的内置运行模板。
  limitations: 随机初始化权重，没有真实语言能力，回答内容没有参考价值。
---

# Tiny Qwen2 无 app.py 运行测试

这个目录故意不包含 `app.py`。上传为模型仓库后，在“运行”标签点击启动，后端会自动使用平台内置的本地 Qwen 运行模板。

它的权重是随机生成的超小 Qwen2 结构，只用于验证：

```text
模型仓库无 app.py -> 平台生成内置运行 app -> 加载 LOCAL_MODEL_PATH -> 打开 Gradio 页面
```

注意：这个模型没有真实问答能力，输出可能为空、重复或无意义。
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
