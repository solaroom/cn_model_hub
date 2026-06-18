"""Build the tiny Qwen2 random-choice model used by quick-evaluation tests."""

from __future__ import annotations

import json
import random
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "models" / "random-choice-qwen2"
DATASET = ROOT / "examples" / "datasets" / "c-eval" / "quick_eval" / "ceval_20.jsonl"

SPECIAL_TOKENS = ["<|endoftext|>", "<|im_start|>", "<|im_end|>", "<unk>"]
BASE_TOKENS = [
    "A", "B", "C", "D", "system", "user", "assistant", "答案", "科目", "题目",
    *list("abcdefghijklmnopqrstuvwxyz_"),
]


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wordlevel_tokens(text: str) -> list[str]:
    """Match the tokenizer's whitespace-only splitting."""
    return text.split()


def build_vocab() -> dict[str, int]:
    tokens = [*SPECIAL_TOKENS, *BASE_TOKENS]
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        subject_parts = re.findall(r"[A-Za-z]+|_[A-Za-z]+", item.get("subject", ""))
        texts = [
            f"科目：{item.get('subject', '')}",
            f"题目：{item['question']}",
            *item["choices"].values(),
            *subject_parts,
        ]
        for text in texts:
            extracted = wordlevel_tokens(str(text))
            tokens.extend(extracted)
    return {token: index for index, token in enumerate(dict.fromkeys(tokens))}


def floats(values: list[float]) -> bytes:
    return struct.pack(f"<{len(values)}f", *values)


def write_safetensors(path: Path, tensors: dict[str, tuple[list[int], bytes]]) -> None:
    header: dict[str, object] = {"__metadata__": {"format": "pt"}}
    offset = 0
    parts: list[bytes] = []
    for name, (shape, raw) in tensors.items():
        header[name] = {
            "dtype": "F32",
            "shape": shape,
            "data_offsets": [offset, offset + len(raw)],
        }
        offset += len(raw)
        parts.append(raw)
    encoded = json.dumps(header, separators=(",", ":")).encode("utf-8")
    encoded += b" " * ((8 - len(encoded) % 8) % 8)
    path.write_bytes(struct.pack("<Q", len(encoded)) + encoded + b"".join(parts))


def main() -> None:
    rng = random.Random(20260618)
    OUT.mkdir(parents=True, exist_ok=True)
    vocab = build_vocab()
    hidden = 64
    intermediate = 128

    config = {
        "architectures": ["Qwen2ForCausalLM"],
        "model_type": "qwen2",
        "vocab_size": len(vocab),
        "hidden_size": hidden,
        "intermediate_size": intermediate,
        "num_hidden_layers": 1,
        "num_attention_heads": 4,
        "num_key_value_heads": 4,
        "max_position_embeddings": 512,
        "rope_theta": 1000000.0,
        "rms_norm_eps": 1e-6,
        "attention_dropout": 0.0,
        "attention_bias": True,
        "mlp_bias": False,
        "bos_token_id": vocab["<|im_start|>"],
        "eos_token_id": vocab["<|im_end|>"],
        "pad_token_id": vocab["<|endoftext|>"],
        "tie_word_embeddings": False,
        "torch_dtype": "float32",
    }
    write_json(OUT / "config.json", config)
    write_json(
        OUT / "generation_config.json",
        {
            "bos_token_id": config["bos_token_id"],
            "eos_token_id": config["eos_token_id"],
            "pad_token_id": config["pad_token_id"],
            "max_new_tokens": 4,
            "do_sample": False,
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
            "model_max_length": 512,
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
    write_json(
        OUT / "tokenizer.json",
        {
            "version": "1.0",
            "truncation": None,
            "padding": None,
            "added_tokens": [
                {
                    "id": vocab[token],
                    "content": token,
                    "single_word": False,
                    "lstrip": False,
                    "rstrip": False,
                    "normalized": False,
                    "special": True,
                }
                for token in SPECIAL_TOKENS
            ],
            "normalizer": None,
            "pre_tokenizer": {"type": "WhitespaceSplit"},
            "post_processor": None,
            "decoder": None,
            "model": {"type": "WordLevel", "vocab": vocab, "unk_token": "<unk>"},
        },
    )

    # Every non-answer output row is zero. The four letter rows read four class
    # coordinates, so only A/B/C/D can win greedy decoding.
    head = [[0.0] * hidden for _ in vocab]
    for answer_class, letter in enumerate("ABCD"):
        head[vocab[letter]][answer_class] = 1.35 if letter == "B" else 1.0

    embeddings = [0.0] * (len(vocab) * hidden)
    ascii_tokens = list("abcdefghijklmnopqrstuvwxyz_")
    random_classes = list(range(4)) * ((len(ascii_tokens) + 3) // 4)
    rng.shuffle(random_classes)
    for token, answer_class in zip(ascii_tokens, random_classes):
        # Qwen2's ByteLevel path falls back to characters when there are no BPE
        # merges. Randomly projecting the ASCII characters in subject names and
        # formula fragments yields a deterministic random baseline per item.
        offset = vocab[token] * hidden
        embeddings[offset + answer_class] = 1.0

    zero_hh = floats([0.0] * (hidden * hidden))
    identity_hh = floats(
        [
            1.0 if row == column else 0.0
            for row in range(hidden)
            for column in range(hidden)
        ]
    )

    tensors: dict[str, tuple[list[int], bytes]] = {
        "model.embed_tokens.weight": ([len(vocab), hidden], floats(embeddings)),
        "model.layers.0.self_attn.q_proj.weight": ([hidden, hidden], zero_hh),
        "model.layers.0.self_attn.k_proj.weight": ([hidden, hidden], zero_hh),
        "model.layers.0.self_attn.v_proj.weight": ([hidden, hidden], identity_hh),
        "model.layers.0.self_attn.o_proj.weight": ([hidden, hidden], identity_hh),
        "model.layers.0.self_attn.q_proj.bias": ([hidden], floats([0.0] * hidden)),
        "model.layers.0.self_attn.k_proj.bias": ([hidden], floats([0.0] * hidden)),
        "model.layers.0.self_attn.v_proj.bias": ([hidden], floats([0.0] * hidden)),
        "model.layers.0.mlp.gate_proj.weight": ([intermediate, hidden], floats([0.0] * (intermediate * hidden))),
        "model.layers.0.mlp.up_proj.weight": ([intermediate, hidden], floats([0.0] * (intermediate * hidden))),
        "model.layers.0.mlp.down_proj.weight": ([hidden, intermediate], floats([0.0] * (hidden * intermediate))),
        "model.layers.0.input_layernorm.weight": ([hidden], floats([1.0] * hidden)),
        "model.layers.0.post_attention_layernorm.weight": ([hidden], floats([1.0] * hidden)),
        "model.norm.weight": ([hidden], floats([1.0] * hidden)),
        "lm_head.weight": ([len(vocab), hidden], floats([value for row in head for value in row])),
    }
    write_safetensors(OUT / "model.safetensors", tensors)


if __name__ == "__main__":
    main()
