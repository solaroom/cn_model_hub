---
license: apache-2.0
language:
  - zh
  - en
library_name: transformers
pipeline_tag: text-generation
base_model: Qwen/Qwen2.5-0.5B-Instruct
tags:
  - qwen
  - qwen2.5
  - chinese
  - local-inference
cn_model:
  display_name: Qwen2.5-0.5B 本地推理示例
  model_family: Qwen2.5
  model_type: causal-lm
  parameter_count: 0.5B
  organization: Alibaba Cloud
  tasks:
    - 中文对话
    - 文本生成
  chinese_capabilities:
    - 中文问答
    - 指令跟随
  inference_frameworks:
    - transformers
  recommended_use: 课堂演示和轻量中文对话验证
  limitations: 0.5B 模型能力有限，复杂推理和长文本表现不如更大模型。
---

# Qwen2.5-0.5B 本地推理示例

这个目录是 `cn_model_hub` 的本地模型推理模板。它和模型仓库页面的“运行”标签配套，用来验证：

```text
上传模型权重 -> 平台物化模型仓库 -> 本地加载模型 -> Gradio 在线对话
```

## 模型仓库文件结构

把 Qwen2.5-0.5B-Instruct 的模型文件放在模型仓库根目录：

```text
README.md
app.py
requirements.txt
config.json
generation_config.json
model.safetensors
tokenizer.json
tokenizer_config.json
vocab.json
merges.txt
```

如果模型仓库没有 `app.py`，`cn_model_hub` 后端会自动使用内置的 Qwen2.5-0.5B 本地推理模板；如果仓库包含这个 `app.py`，则运行仓库自带模板。

## 下载模型文件

可以从 Hugging Face 下载到本地后上传到模型仓库：

```bash
huggingface-cli download Qwen/Qwen2.5-0.5B-Instruct \
  --local-dir ./qwen2.5-0.5b-local \
  --local-dir-use-symlinks False
```

然后把本目录里的 `app.py`、`requirements.txt`、`README.md` 和下载下来的模型文件一起上传到 `cn_model_hub` 模型仓库。

## 运行

进入模型仓库页面，打开“运行”，点击“启动”。运行时会设置：

```bash
LOCAL_MODEL_PATH=<当前模型仓库物化目录>
PORT=<动态端口>
GRADIO_ROOT_PATH=/api/models/<namespace>/<name>/runtime/proxy
```

模板使用：

```python
AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH, local_files_only=True)
AutoModelForCausalLM.from_pretrained(LOCAL_MODEL_PATH, local_files_only=True)
```

所以推理使用的是平台模型仓库里的本地文件，不是外部 API。
