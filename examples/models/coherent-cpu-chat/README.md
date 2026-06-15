---
license: apache-2.0
language:
  - zh
library_name: gradio
pipeline_tag: text-generation
tags:
  - cpu
  - chinese
  - local-inference
  - demo
cn_model:
  display_name: Coherent CPU Chat 轻量中文对话示例
  model_family: TemplateChat
  model_type: retrieval-template-chat
  parameter_count: no-neural-weights
  tasks:
    - 中文对话
    - 平台运行演示
  chinese_capabilities:
    - 中文问答
    - 结构化回答
  inference_frameworks:
    - gradio
  recommended_use: CPU 环境下的平台运行页演示、课堂展示和联调验证。
  limitations: 这是轻量检索与模板对话示例，不是真正训练过的大语言模型；开放域知识和复杂推理能力有限。
---

# Coherent CPU Chat 轻量中文对话示例

这个示例用来替代 `tiny-qwen2-no-app` 做演示。`tiny-qwen2-no-app` 是随机初始化权重，适合验证加载链路，但输出没有语言能力；本目录提供一个可以直接在 CPU 上运行的 `app.py`，回答至少是连贯中文。

## 特点

- 不需要 GPU。
- 不下载外部权重。
- 启动快，依赖只有 Gradio。
- 回答由轻量意图匹配和模板生成，适合平台演示和课堂讲解。

## 运行

在模型仓库页面打开“运行”，点击“启动”。平台会执行本目录的 `app.py`，并传入：

```bash
PORT=<动态端口>
GRADIO_ROOT_PATH=/api/models/<namespace>/<name>/runtime/proxy
```

本示例不要求 `LOCAL_MODEL_PATH` 中存在神经网络权重。

## 与真实小模型的区别

这个示例的目标是“能在 CPU 上稳定说人话”，不是追求真实大模型能力。如果需要真实语言模型，可以继续使用 `examples/models/qwen2.5-0.5b-local`，下载并上传 `Qwen/Qwen2.5-0.5B-Instruct` 的权重；它也能在 CPU 上跑，只是速度和内存占用会明显高于本示例。
