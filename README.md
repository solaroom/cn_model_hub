# cn_model_hub

中文开源 AI 模型社区 `cn_model_hub` 是一个面向中文模型生态的轻量级模型托管平台。项目参考 Hugging Face Hub 的核心使用方式，完成了用户系统、模型仓库、数据集仓库、Space/Demo、中文搜索、智能助手、快速评测、排行榜、MLflow 实验追踪和 Docker Compose 部署能力。

本仓库为课程结题提交版源码，已整理为可阅读、可部署、可测试的完整项目结构。提交包不包含依赖目录、运行缓存、数据库数据和模型权重文件。

## 项目完成情况

| 模块 | 完成内容 | 状态 |
| --- | --- | --- |
| 用户系统 | 注册、登录、Session、Token、个人主页、头像 | 完成 |
| 组织和权限 | 组织、邀请、公开/私有仓库权限 | 完成 |
| 仓库系统 | model/dataset/space 仓库、README、文件树、提交记录 | 完成 |
| 文件系统 | 上传前检查、LFS 大文件、下载、预览 | 完成 |
| 搜索系统 | Meilisearch、中文别名、数据库回退 | 完成 |
| 智能助手 | 平台知识库问答、资源搜索聚合、可选 LLM 整理 | 完成 |
| Space/Demo | 本地 Gradio Demo、模型/Space 仓库运行入口 | 完成 |
| 远端 GPU | 可选 Runtime Agent，把 Demo 和评测切换到远端 GPU 执行 | 完成 |
| 快速评测 | C-Eval 样本评测、EvaluationRun、排行榜 | 完成 |
| MLflow | Tracking Server 集成、仓库绑定信息 | 完成 |
| 部署 | Docker Compose、本地演示环境、部署说明 | 完成 |
| 测试 | 后端 pytest、前端 Vitest、人工验收用例 | 完成 |

## 技术栈

- 后端：FastAPI、Peewee、PostgreSQL、Uvicorn
- 前端：Vue 3、Vite、Pinia、UnoCSS、Vitest
- 存储：LakeFS、MinIO/S3、LFS 大文件管理
- 搜索：Meilisearch，支持中文模型别名和数据库回退
- 缓存：Valkey
- AI 能力：Transformers、Gradio、C-Eval 快速评测、智能助手 RAG
- 实验追踪：MLflow Tracking Server
- 部署：Docker、Docker Compose、Nginx，可选远端 GPU Runtime Agent

## 目录结构

```text
cn_model_hub/
├── src/cn_model_hub/              # FastAPI 后端、API、认证、仓库、搜索、评测、Space 运行逻辑
├── src/cn-model-hub-ui/           # 用户前台，包含模型、数据集、Space、排行榜、助手页面
├── test/cn_model_hub/             # 后端 pytest 测试
├── test/cn-model-hub-ui/          # 前端 Vitest 测试
├── docs/platform-knowledge/       # 智能助手平台知识库
├── scripts/dev/                   # 本地初始化、演示数据和开发辅助脚本
├── scripts/db_migrations/         # 数据库迁移脚本
├── scripts/remote_runtime_agent.py # 可选远端 GPU Runtime Agent
├── docker/                        # Nginx、LakeFS 和容器启动相关配置
├── images/                        # Logo、站点图标和品牌素材
├── Dockerfile                     # 后端容器构建文件
├── docker-compose.yml             # 本地完整演示环境
├── config-example.toml            # 配置模板
├── .env.dev.example               # 本地开发环境变量模板
├── pyproject.toml                 # Python 项目依赖和打包配置
├── package.json                   # 前端 workspace 脚本
└── README.md                      # 项目说明
```

运行过程中会生成 `hub-meta/`、`hub-storage/`、`.space-runtimes/`、`src/cn-model-hub-ui/dist/`、`logs/` 等目录，这些属于运行数据或构建产物，不作为源码提交内容。

## 快速运行

### 1. 准备环境

建议使用以下版本：

- Python 3.10+
- Node.js 20+
- pnpm 10+
- Docker Desktop / Docker Compose

复制配置模板：

```bash
cp .env.dev.example .env.dev
cp config-example.toml config.toml
```

安装前端依赖并构建页面：

```bash
pnpm install
pnpm run build
```

安装后端开发依赖：

```bash
python -m pip install -e ".[dev,assistant]"
```

### 2. 启动 Docker Compose 环境

```bash
docker compose up -d --build
```

只重建平台后端和前端：

```bash
docker compose up -d --build hub-api hub-ui
```

查看服务状态：

```bash
docker compose ps
```

停止服务：

```bash
docker compose down
```

## 访问地址

| 服务 | 地址 |
| --- | --- |
| 前台页面 | http://127.0.0.1:28080 |
| 后端 API | http://127.0.0.1:48888 |
| API 文档 | http://127.0.0.1:48888/docs |
| LakeFS | http://127.0.0.1:28000 |
| MinIO 控制台 | http://127.0.0.1:29000 |
| Meilisearch | http://127.0.0.1:27700 |
| MLflow | http://127.0.0.1:25000 |

## 演示账号和本地配置

| 项目 | 值 |
| --- | --- |
| Meilisearch Key | `dev-meili-master-key` |
| MinIO | `minioadmin / minioadmin` |

Docker Compose 中使用的是本地演示配置，生产环境部署时应替换 `CN_MODEL_HUB_SESSION_SECRET`、`CN_MODEL_HUB_ADMIN_SECRET_TOKEN`、数据库密码、MinIO 密钥和 LLM API Key。不要把真实 API Key、远端 Runtime Agent Key、服务器地址或 SSH 凭据提交到仓库。

## 核心功能说明

### 模型和数据集仓库

平台支持创建 `model`、`dataset`、`space` 三类仓库。用户可以上传文件、查看 README、浏览文件树、下载资源、查看提交记录，并通过 LakeFS + MinIO/S3 管理文件版本和对象存储。

### 中文搜索

搜索服务接入 Meilisearch，支持模型、数据集和 Space 的统一检索。搜索逻辑中包含中文关键词扩展和模型别名映射。搜索索引不可用时，后端会回退到数据库查询，保证演示流程不中断。

重建搜索索引：

```bash
curl -X POST http://127.0.0.1:48888/api/search/index/rebuild \
  -H "Authorization: Bearer <your-token>"
```

查看索引状态：

```bash
curl http://127.0.0.1:48888/api/search/index/status
```

### 智能助手

智能助手位于：

```text
http://127.0.0.1:28080/assistant
```

助手会检索 `docs/platform-knowledge/` 中的平台知识，并结合站内搜索接口返回模型、数据集或 Space 资源链接。若配置了外部 OpenAI 兼容 LLM API Key，后端会调用大模型整理答案；未配置时，仍会返回本地检索结果。

可选 LLM 配置示例：

```bash
export CN_MODEL_HUB_ASSISTANT_LLM_API_KEY="<your-api-key>"
export CN_MODEL_HUB_ASSISTANT_LLM_BASE_URL="<llm-compatible-base-url>"
export CN_MODEL_HUB_ASSISTANT_LLM_MODEL="<llm-model-name>"
docker compose up -d --force-recreate hub-api
```

### Space/Demo

Space 页面支持模型或仓库 Demo 的运行入口。后端会同步仓库文件，启动 Gradio 运行时，并把运行地址返回给前端页面，便于在平台内直接体验模型资源。

若配置远端 GPU Runtime Agent，模型仓库页的“运行”和快速评测可以切换到远端 GPU 执行；未配置时默认使用本地运行时。

远端 GPU 配置示例：

```bash
CN_MODEL_HUB_SPACE_RUNTIME_BACKEND=remote
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_BASE_URL=<runtime-agent-base-url>
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_API_KEY=<runtime-agent-key>
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_UPLOAD_METHOD=ssh
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_SSH_ALIAS=<ssh-alias>
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_ROOT=<remote-runtime-root>
```

远端 Agent 脚本位于 `scripts/remote_runtime_agent.py`。具体服务器地址、监听端口、SSH 别名和密钥应在部署环境中配置，不写入仓库。

### 快速评测和排行榜

快速评测用于课程演示中的模型效果闭环：

1. 用户进入模型页面。
2. 选择快速评测。
3. 后端创建 EvaluationRun。
4. 使用 C-Eval 样本进行评测。
5. 将准确率写入排行榜。
6. 首页和排行榜页展示模型排名。

完整榜单页面：

```text
/leaderboards/generative-llm
```

### MLflow 实验追踪

项目集成 MLflow Tracking Server，用于展示模型实验追踪和评测相关信息。Docker Compose 中的 `mlflow` 服务提供本地演示环境，后端通过 `MLFLOW_TRACKING_URI` 连接到该服务。

## 测试

运行后端测试：

```bash
python -m pytest
```

运行前端测试：

```bash
pnpm test
```

运行前端构建检查：

```bash
pnpm run build
```

## 验收要点

- 前台页面可以访问。
- API 文档可以访问。
- 演示账号可以登录。
- 模型、数据集、Space 页面存在并可浏览。
- 文件上传、下载、README 展示和文件树可用。
- 中文搜索和智能助手可演示。
- Space/Demo 可以从页面进入。
- 快速评测和排行榜形成闭环。
- Docker Compose 可以启动本地演示环境。
- 提交包不包含依赖目录、运行缓存和数据库数据。

## 项目成员分工

略

## 提交说明

本源码目录用于课程结题提交，配套 PDF 文档位于提交包的 `项目文档/` 目录和根目录中。源码保留必要配置、脚本、测试和说明文件，运行生成的数据目录不随提交包附带。
