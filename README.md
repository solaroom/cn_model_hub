# cn_model_hub

`cn_model_hub` 是一个面向中文开源 AI 模型的自托管模型社区项目。它基于 FastAPI、Vue 3、LakeFS、MinIO/S3 和 PostgreSQL，提供模型、数据集、在线 Demo Space 和实验追踪的统一入口。

## 当前功能

- 模型、数据集、Space 仓库创建、上传、浏览和下载
- Hugging Face Hub 风格的 API 路由和文件解析路径
- LakeFS 版本管理，支持分支、提交记录和文件树
- MinIO/S3 对象存储，支持大文件和 LFS 上传
- Vue 3 前台页面和独立管理后台
- 本地模型运行：模型仓库页面可直接启动本地推理 demo，默认支持 Qwen2.5-0.5B 类 Transformers CausalLM
- 简化 Space 运行时：运行仓库根目录的 `app.py`，适合 Gradio 类 demo
- 中文模型元数据规范：通过 README frontmatter 展示模型家族、参数量、中文能力、推理框架和中文评测结果
- Meilisearch 中文模型搜索：索引仓库名、作者、类型和中文模型别名，服务不可用时自动回退数据库搜索
- MLflow Tracking 集成，用于记录实验、指标和 artifact

## 快速启动

先构建前端，再启动 Docker 服务：

```bash
pnpm install
pnpm run build
docker compose up -d --build
```

访问地址：

- 前台页面：http://127.0.0.1:28080
- 管理后台：http://127.0.0.1:28080/admin
- API 文档：http://127.0.0.1:48888/docs
- LakeFS：http://127.0.0.1:28000
- MinIO：http://127.0.0.1:29000
- Meilisearch：http://127.0.0.1:27700
- MLflow：http://127.0.0.1:25000

## 搜索

Docker Compose 已包含 `meilisearch` 服务。API 优先使用 Meilisearch 搜索模型、数据集和 Space；如果 Meilisearch 未启动或不可用，会自动回退到数据库搜索。

搜索状态：

```bash
curl http://127.0.0.1:48888/api/search/index/status
```

首次接入或已有仓库需要重建索引：

```bash
curl -X POST http://127.0.0.1:48888/api/search/index/rebuild \
  -H "X-Admin-Token: dev-admin-token-change-me"
```

本地开发配置：

```bash
KOHAKU_HUB_MEILISEARCH_ENABLED=true
KOHAKU_HUB_MEILISEARCH_URL=http://127.0.0.1:27700
KOHAKU_HUB_MEILISEARCH_API_KEY=dev-meili-master-key
```

## 本地模型推理

模型仓库页面也有“运行”标签。点击“启动”后，后端会：

1. 从 LakeFS 同步当前模型仓库 revision 的文件
2. 如果仓库有 `app.py`，运行仓库自带 demo
3. 如果仓库没有 `app.py`，自动使用内置 Qwen2.5-0.5B 本地推理模板
4. 使用 `LOCAL_MODEL_PATH=<模型仓库物化目录>` 加载本地权重
5. 通过 `/api/models/{namespace}/{name}/runtime/proxy/` 代理到前端 iframe

这条链路跑的是上传到模型仓库里的本地模型文件，不是外部 API。内置模板等价于：

```python
AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH, local_files_only=True)
AutoModelForCausalLM.from_pretrained(LOCAL_MODEL_PATH, local_files_only=True)
```

Qwen2.5-0.5B 示例模板在：

```text
examples/models/qwen2.5-0.5b-local/
```

模型仓库推荐文件结构：

```text
README.md
app.py                  # 可选；没有时使用平台内置本地 Qwen 模板
requirements.txt        # 可选；没有时使用平台内置本地 Qwen 依赖
config.json
generation_config.json
model.safetensors
tokenizer.json
tokenizer_config.json
vocab.json
merges.txt
```

下载 Qwen2.5-0.5B-Instruct 文件：

```bash
huggingface-cli download Qwen/Qwen2.5-0.5B-Instruct \
  --local-dir ./qwen2.5-0.5b-local \
  --local-dir-use-symlinks False
```

## Space Demo

Space 仓库上传后，只需要在仓库根目录提供 `app.py`。如果有依赖，放在 `requirements.txt`：

```text
app.py
requirements.txt
README.md
```

进入 Space 仓库页面后打开“运行”标签，点击“启动”。后端会：

1. 从 LakeFS 同步该 Space 当前 revision 的文件
2. 可选安装 `requirements.txt`
3. 运行 `python app.py`
4. 通过 `/api/spaces/{namespace}/{name}/runtime/proxy/` 代理到前端 iframe

运行环境会注入这些变量，千问或其他对话 demo 可以直接读取：

```bash
PORT
GRADIO_SERVER_NAME
GRADIO_SERVER_PORT
GRADIO_ROOT_PATH
CN_MODEL_HUB_SPACE_ID
MLFLOW_TRACKING_URI
```

## MLflow

项目的 Docker Compose 已包含 `mlflow` 服务。它使用本地 `mlflow-master/` 源码启动 MLflow Tracking Server，数据保存在：

```text
hub-meta/mlflow-data/
```

API 和 Space 运行时会收到：

```bash
MLFLOW_TRACKING_URI=http://mlflow:5000
KOHAKU_HUB_MLFLOW_TRACKING_URI=http://mlflow:5000
```

本地开发时可以使用 `.env.dev.example` 中的：

```bash
MLFLOW_TRACKING_URI=http://127.0.0.1:25000
```

## 常用开发命令

```bash
pnpm run dev:ui
pnpm run dev:admin
pytest
```

## 当前进度

阶段一 MVP 约 80%-85%：

- 已完成用户注册/登录、Token、仓库创建/删除/移动
- 已完成模型、数据集、Space 的文件上传、下载、文件树、README 展示
- 已完成 LakeFS 版本管理、MinIO/S3 大文件存储、LFS 基础链路
- 已完成中文模型元数据规范和模型页展示
- 已接入 Meilisearch，搜索可按中文别名召回模型，并带数据库兜底
- 待补：真实演示数据、上传模型卡强校验、完整课堂演示流程复测

阶段二 社区和在线 Demo 约 65%-75%：

- 已完成点赞和基础讨论 API
- 已完成 Space 运行时，可运行 Gradio `app.py`
- 已完成模型仓库本地推理运行时，可直接运行 Qwen2.5-0.5B 类本地模型
- 已完成 MLflow Tracking 基础接入
- 待补：讨论前端体验、Space/模型运行密钥和环境变量管理、运行隔离、资源限制、持久日志、Streamlit 支持

## 下一步

建议队友接手时按这个顺序推进：

1. 开 Docker 后跑全链路：注册用户 -> 创建模型 -> 上传 Qwen2.5-0.5B 文件 -> 启动模型运行 -> 对话。
2. 重建 Meilisearch 索引并验证中文搜索：
   `POST /api/search/index/rebuild`。
3. 给 Space/模型运行时增加环境变量和密钥配置页面。
4. 把讨论功能补成完整前端体验。
5. 做阶段三：中文评测榜单、评测任务提交、MLflow run 和模型仓库绑定。

## 说明

`mlflow-master/` 是本地 MLflow 源码挂载目录，默认不提交到本仓库。Space 运行缓存、MinIO 数据和数据库数据也不会提交，分别位于 `.space-runtimes/`、`hub-storage/` 和 `hub-meta/`。
