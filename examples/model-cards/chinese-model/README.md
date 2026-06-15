---
license: apache-2.0
language:
  - zh
  - en
library_name: transformers
pipeline_tag: text-generation
base_model:
  - Qwen/Qwen2.5-7B
tags:
  - chinese
  - chat
  - qwen
cn_model:
  display_name: 中文千问示例模型
  model_family: Qwen
  model_type: causal-lm
  parameter_count: 7B
  context_length: 32768
  organization: 示例团队
  release_date: 2026-06-15
  base_model: Qwen/Qwen2.5-7B
  tasks:
    - 对话
    - 文本生成
    - 中文问答
  chinese_capabilities:
    - 中文知识问答
    - 中文写作
    - 代码解释
    - 摘要生成
  domains:
    - 通用
    - 教育
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
    - 教学演示
    - 轻量文本生成
  limitations:
    - 不保证事实完全准确
    - 不适合医疗、法律、金融等高风险决策
  commercial_use: allowed
  contact: model-team@example.com
eval_results_chinese:
  - benchmark: C-Eval
    split: test
    metric: accuracy
    score: 72.5
  - benchmark: CMMLU
    split: test
    metric: accuracy
    score: 70.1
---

# 中文千问示例模型

这里写模型介绍、训练数据来源、推理方式、使用示例和注意事项。

## 快速使用

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "your-namespace/your-model"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto")
```
