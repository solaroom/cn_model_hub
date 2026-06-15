---
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
