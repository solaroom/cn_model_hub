# Space 和在线 Demo

Space 是平台中的在线 Demo 仓库。它的核心意义是展示已经创建的 Demo，并提供入口让用户直接进入演示界面。

当前项目实现的是简化版 Space 功能，目标是满足课堂演示和本地模型验证：能运行 Qwen2.5-0.5B-Instruct 的 Gradio 对话 Demo。

## Demo 模板

当前固定支持的基础模板包含：

- `app.py`：Gradio 应用入口。
- `requirements.txt`：Demo 依赖。
- `README.md`：Demo 说明。

运行时平台会为 Space 分配端口，设置必要环境变量，并把模型路径传给 Demo。Qwen2.5 Demo 使用本地 Transformers 模型文件进行推理，而不是调用外部模型 API。

## 本地模型推理

当前已实现 Qwen2.5-0.5B-Instruct 本地推理模式。Demo 会加载平台保存的本地模型文件，使用 Transformers 生成回复。这样用户看到某个模型后，点击 Demo 体验的就是平台里托管的本地模型。

## 当前限制

- 当前只重点保证 Qwen2.5-0.5B-Instruct 这一类 Transformers 文本生成模型可演示。
- 其他 Transformers 模型如果结构、tokenizer 和生成方式兼容，有机会运行，但尚未做通用模板适配。
- 暂未实现 GPU 调度、资源隔离、队列和多租户运行治理。

