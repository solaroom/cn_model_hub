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
  display_name: Qwen2.5-0.5B-Instruct
  model_family: Qwen2.5
  model_type: causal-lm
  parameter_count: 0.49B
  organization: Alibaba Cloud
  architecture: Transformer with RoPE, SwiGLU, RMSNorm, attention QKV bias, tied word embeddings
  training_stage: Pretraining and post-training
  layers: 24
  attention_heads: "Q: 14, KV: 2"
  context_length: 32768
  generation_length: 8192
  tasks:
    - 中文对话
    - 文本生成
    - 指令跟随
  chinese_capabilities:
    - 中文问答
    - 指令跟随
    - 长文本生成
    - 结构化输出
  inference_frameworks:
    - transformers
  recommended_use: 轻量中文对话、指令跟随、课堂演示和本地推理验证
  limitations: 0.5B 模型能力有限，复杂推理和长文本表现不如更大模型。
---

# Qwen2.5-0.5B-Instruct

## 介绍

Qwen2.5 是 Qwen 大型语言模型的最新系列。对于 Qwen2.5，我们发布了从 0.5 到 720 亿参数的基础语言模型和指令调优语言模型。Qwen2.5 相较于 Qwen2 带来了以下改进：

- 显著更多的知识，并且在编程和数学方面的能力得到了极大的提升，这得益于我们在这些领域专门训练的专家模型。
- 在遵循指令、生成长文本（超过 8K tokens）、理解结构化数据（例如表格）和生成结构化输出（特别是 JSON）方面有显著改进。对系统提示的多样性更具适应性，增强了角色扮演实现和聊天机器人的条件设置。
- 长上下文支持可达 128K tokens，并且可以生成最多 8K tokens。
- 多语言支持，包括中文、英语、法语、西班牙语、葡萄牙语、德语、意大利语、俄语、日语、韩语、越南语、泰语、阿拉伯语等超过 29 种语言。

此仓库包含的是经过指令调优的 0.5B 参数的 Qwen2.5 模型，其具有以下特点：

- 类型：因果语言模型
- 训练阶段：预训练 & 后训练
- 架构：带有 RoPE、SwiGLU、RMSNorm、注意力 QKV 偏置和绑定词嵌入的变换器
- 参数数量：0.49B
- 非嵌入参数数量：0.36B
- 层数：24
- 注意力头数（GQA）：Q 为 14，KV 为 2
- 上下文长度：完整 32,768 tokens，生成 8192 tokens

更多详情，请参阅我们的博客、GitHub 和文档。
