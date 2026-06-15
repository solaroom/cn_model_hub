---
title: 千问对话 Demo
emoji: 💬
sdk: gradio
app_file: app.py
models:
  - qwen-plus
tags:
  - qwen
  - chat
  - chinese
---

# 千问对话 Demo

这是 `cn_model_hub` 的固定 Space 模板，包含：

- `app.py`
- `requirements.txt`
- `README.md`

## 环境变量

必填其一：

```bash
DASHSCOPE_API_KEY=sk-...
QWEN_API_KEY=sk-...
```

可选：

```bash
QWEN_MODEL=qwen-plus
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_SYSTEM_PROMPT=你是中文开源AI模型社区里的千问助手。
```

上传到 Space 仓库后，在仓库页打开“运行”，点击“启动”即可。
