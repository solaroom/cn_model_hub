# cn_model_hub

`cn_model_hub` 是一个面向中文开源 AI 模型的社区平台，目标是做一个更偏中文模型生态的轻量 Hugging Face Hub：支持模型托管、数据集管理、在线 Demo、中文搜索、快速评测、排行榜、MLflow 实验追踪和站内智能助手。

## 当前可演示功能

- 用户系统：注册、登录、个人主页、Token、基础权限。
- 模型托管：创建模型仓库、上传/下载文件、README 模型卡片、文件树、提交记录。
- 数据集管理：创建数据集仓库、上传数据文件、README 展示、结构化数据预览。
- Space Demo：展示已创建 Demo，并从空间页直接进入在线演示界面。
- 本地模型推理：当前重点支持 `Qwen2.5-0.5B-Instruct` 这类 Transformers 文本生成模型。
- 中文模型元数据：展示模型家族、类型、参数量、上下文长度、中文能力、推理框架和标签。
- 中文搜索：接入 Meilisearch，支持模型/数据集/Space 搜索；服务不可用时回退数据库搜索。
- 快速评测：支持 Qwen2.5 类型模型用 C-Eval 抽样 20 题评测。
- 排行榜：首页和榜单页展示生成式大语言模型排行榜前十名。
- MLflow：模型页展示实验跟踪信息，Docker Compose 集成 MLflow Tracking Server。
- 智能助手：回答平台怎么用，并调用站内搜索找模型或数据集，返回来源和真实链接。

## 项目结构

```text
cn_model_hub/
├── src/cn_model_hub/              # FastAPI 后端、数据库模型、搜索、评测、Space 运行时
├── src/cn-model-hub-ui/           # 用户前台：模型、数据集、空间、排行榜、助手
├── src/cn-model-hub-admin/        # 管理后台：用户、仓库、存储、缓存、健康状态
├── docs/platform-knowledge/       # 平台中文知识库，智能助手只索引这个目录
├── examples/models/               # 演示模型模板，例如 Qwen2.5 本地 Demo
├── examples/datasets/             # 演示数据集，例如 C-Eval 20 题快速评测样本
├── scripts/dev/                   # 本地初始化、演示数据和验证脚本
├── scripts/db_migrations/         # 数据库迁移脚本
├── docker/                        # Nginx、LakeFS 和后端启动脚本
├── images/                        # 站点图标和品牌素材
├── docker-compose.yml             # 本地演示部署
├── pyproject.toml                 # Python 后端依赖
└── package.json                   # 前端 workspace 脚本
```

`mlflow-master/` 是用户本地放入的 MLflow 源码目录，用于启动 MLflow 服务；`hub-meta/`、`hub-storage/`、`.space-runtimes/` 是运行数据和缓存目录，不作为项目源码提交。

## 部署方式

先安装前端依赖并构建静态页面：

```bash
pnpm install
pnpm run build
```

启动完整本地演示环境：

```bash
docker compose up -d --build
```

只重建平台后端和前端：

```bash
docker compose up -d --build hub-api hub-ui
```

常用访问地址：

- 前台页面：http://127.0.0.1:28080
- 管理后台：http://127.0.0.1:28080/admin
- 后端 API：http://127.0.0.1:48888
- API 文档：http://127.0.0.1:48888/docs
- LakeFS：http://127.0.0.1:28000
- MinIO 控制台：http://127.0.0.1:29000
- Meilisearch：http://127.0.0.1:27700
- MLflow：http://127.0.0.1:25000

## 演示账号

- 普通用户：`mai_lin`
- 密码：`CnModelHub123!`
- 管理后台令牌：`dev-admin-token-change-me`
- Meilisearch Key：`dev-meili-master-key`
- MinIO：`minioadmin / minioadmin`

## 演示数据

- 模型：`qwen_demo/qwen2.5-0.5b-instruct`
- 展示名：`Qwen2.5-0.5B-Instruct`
- 数据集：`c-eval`
- Space：Qwen2.5 对话 Demo
- 快速评测：C-Eval 20 题
- 榜单：生成式大语言模型排行榜

## 智能助手

助手入口：

```text
http://127.0.0.1:28080/assistant
```

后端接口：

```bash
curl -X POST http://127.0.0.1:48888/api/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"帮我找 Qwen2.5 0.5B 的模型，并解释怎么运行 Demo"}'
```

处理流程：

```text
用户问题
-> Agent 判断意图
   -> 平台知识问答：检索 docs/platform-knowledge
   -> 找模型/数据集：调用现有搜索接口
   -> 两者都有：搜索接口 + RAG
-> DeepSeek 整理结果
-> 返回答案、来源和真实平台链接
```

RAG embedding 模型配置为 `BAAI/bge-small-zh-v1.5`。DeepSeek API Key 不写入仓库，请通过环境变量注入：

```bash
export DEEPSEEK_API_KEY="你的 DeepSeek API Key"
export CN_MODEL_HUB_ASSISTANT_LLM_MODEL=deepseek-chat
docker compose up -d --force-recreate hub-api
```

如果没有配置 key，助手仍会返回本地检索整理结果，并在接口的 `llm.error` 中说明未启用大模型整理。

## 搜索和索引

Docker Compose 已包含 Meilisearch。重建站内搜索索引：

```bash
curl -X POST http://127.0.0.1:48888/api/search/index/rebuild \
  -H "X-Admin-Token: dev-admin-token-change-me"
```

查看索引状态：

```bash
curl http://127.0.0.1:48888/api/search/index/status
```

## 本地模型 Demo

模型仓库页面的“运行”功能会从 LakeFS 同步当前模型文件，然后启动 Gradio Demo。若仓库提供 `app.py`，优先运行仓库自带 Demo；若没有，则使用内置 Qwen2.5 本地推理模板。

当前重点保证以下文件结构可跑通：

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

这条链路加载的是平台中托管的本地模型文件，不是外部模型 API。

## 快速评测

当前快速评测面向课堂演示，范围是 Qwen2.5 类型生成式大语言模型：

1. 用户上传或打开 Qwen2.5-0.5B-Instruct 模型。
2. 在模型页进入评测区域。
3. 点击快速评测。
4. 后端使用 C-Eval 20 题样本评测。
5. 按准确率写入生成式大语言模型排行榜。

排名标准：C-Eval 20 题准确率从高到低排序；首页展示前十名，完整页为 `/leaderboards/generative-llm`。

## 当前进度

阶段一 MVP：约 85%。

- 已完成用户系统、模型/数据集上传下载、README 展示、文件树、提交记录。
- 已完成 LakeFS 版本管理、MinIO/S3 对象存储、基础 LFS。
- 已完成中文模型元数据展示和 Meilisearch 搜索。
- 待加强：上传流程的错误提示、模型元数据强校验、课堂演示脚本自动化。

阶段二 社区和 Demo：约 70%。

- 已完成点赞、讨论 API、Space 运行时、Qwen2.5 本地 Demo、MLflow 基础集成。
- 已完成 C-Eval 20 题快速评测和排行榜。
- 待加强：讨论前端体验、Space 资源隔离、运行日志、环境变量/密钥配置、更多 Demo 模板。

阶段三 评测和 MLOps：约 35%。

- 已有 MLflow 和快速评测雏形。
- 待加强：完整 C-Eval、更多中文基准、异步评测队列、评测报告、MLflow run 自动记录、DVC/lakeFS 更完整协作流程。

## 下一步建议

1. 把 Qwen2.5 Demo、C-Eval 快速评测和排行榜整理成一键演示脚本。
2. 给模型上传页增加 Transformers 类型校验和更明确的错误提示。
3. 给 Space 运行时增加日志面板、停止/重启、资源限制和环境变量配置。
4. 扩展评测任务：更多题量、更多模型类型、分科目榜单。
5. 让 MLflow 自动记录每次快速评测的参数、指标和 artifact。
