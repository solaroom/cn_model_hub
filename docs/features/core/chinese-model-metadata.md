# 中文模型元数据规范

模型 README 顶部使用 YAML frontmatter 描述元数据。通用字段沿用 Hugging Face 风格，例如 `license`、`language`、`library_name`、`pipeline_tag`、`base_model`、`tags`。

中文模型扩展字段放在 `cn_model` 下：

```yaml
---
license: apache-2.0
language:
  - zh
library_name: transformers
pipeline_tag: text-generation
base_model:
  - Qwen/Qwen2.5-7B
tags:
  - chinese
  - chat
cn_model:
  display_name: 中文千问示例模型
  model_family: Qwen
  model_type: causal-lm
  parameter_count: 7B
  context_length: 32768
  organization: 示例团队
  tasks:
    - 对话
    - 中文问答
  chinese_capabilities:
    - 中文知识问答
    - 中文写作
  domains:
    - 通用
  input_modalities:
    - text
  output_modalities:
    - text
  inference_frameworks:
    - transformers
    - vllm
  quantization:
    - fp16
    - int4
  recommended_use:
    - 中文问答助手
  limitations:
    - 不适合高风险决策
  commercial_use: allowed
eval_results_chinese:
  - benchmark: C-Eval
    split: test
    metric: accuracy
    score: 72.5
---
```

## 字段说明

- `display_name`: 中文展示名
- `model_family`: 模型系列，例如 Qwen、GLM、Baichuan、DeepSeek
- `model_type`: 模型类型，例如 causal-lm、embedding、reranker、vlm
- `parameter_count`: 参数量，例如 7B、14B
- `context_length`: 上下文长度
- `tasks`: 面向用户的任务名称
- `chinese_capabilities`: 中文能力标签
- `domains`: 适用领域
- `inference_frameworks`: 推荐推理框架
- `quantization`: 可用精度或量化格式
- `recommended_use`: 推荐用途
- `limitations`: 使用限制
- `eval_results_chinese`: 中文评测结果列表
