# cn_model_hub

`cn_model_hub` 是一个面向中文开源 AI 模型的社区平台，参考 Hugging Face Hub 的核心使用体验，提供模型托管、数据集管理、在线 Demo、中文搜索、快速评测、排行榜、MLflow 实验追踪和站内智能助手。

## 功能概览

- 用户与权限：注册、登录、个人主页、访问 Token、基础权限控制。
- 模型仓库：创建模型仓库、上传/下载文件、README 模型卡片、文件树和提交记录。
- 数据集仓库：上传数据文件、README 展示、Parquet/JSON 等结构化数据预览。
- Space Demo：支持仓库内 `app.py` 或内置模型 Demo 模板，在线运行 Gradio 应用。
- 中文模型元数据：展示模型家族、任务类型、参数量、上下文长度、推理框架、中文能力和标签。
- 中文搜索：接入 Meilisearch，支持模型、数据集、Space 搜索；搜索服务不可用时回退数据库搜索。
- 快速评测：对 Qwen2.5 类生成式模型使用 C-Eval 20 题样本进行快速评测。
- 排行榜：首页和榜单页展示生成式大语言模型排名。
- MLflow：模型页展示实验追踪信息，Docker Compose 集成 MLflow Tracking Server。
- 智能助手：基于平台知识库和站内搜索回答使用问题，并返回来源链接。
- 远端 GPU：本地平台作为控制面，可把 Space Demo 和快速评测切换到远端 GPU Runtime Agent 执行。

## 技术栈

- 后端：FastAPI、Peewee、PostgreSQL、S3/MinIO、LakeFS、Meilisearch、MLflow。
- 前端：Vue 3、Vite、UnoCSS、Pinia、Vitest。
- Demo/推理：Gradio、Transformers、PyTorch。
- 部署：Docker Compose；远端 GPU 通过 SSH 上传运行包并调用 Runtime Agent。

## 项目结构

```text
cn_model_hub/
├── src/cn_model_hub/              # FastAPI 后端、数据库模型、搜索、评测、Space 运行时
├── src/cn-model-hub-ui/           # Vue 前端
├── docs/platform-knowledge/       # 智能助手检索的中文知识库
├── examples/models/               # 演示模型模板
├── examples/datasets/             # C-Eval 快速评测样本等演示数据
├── examples/spaces/               # Space Demo 示例
├── scripts/dev/                   # 本地初始化、演示数据和验证脚本
├── scripts/db_migrations/         # 数据库迁移脚本
├── scripts/remote_runtime_agent.py # 远端 GPU Runtime Agent
├── docker/                        # Nginx、LakeFS 和后端启动脚本
├── docker-compose.yml             # 本地演示部署
├── config-example.toml            # 配置模板
└── .env.dev.example               # 本地开发环境变量模板
```

运行数据和缓存目录包括 `hub-meta/`、`hub-storage/`、`.space-runtimes/`、`logs/`，不作为项目源码提交。

## 本地部署

### 1. 准备环境

需要安装：

- Python 3.10+
- Node.js 20+
- pnpm 10+
- Docker 和 Docker Compose

首次运行可复制配置模板：

```bash
cp .env.dev.example .env.dev
cp config-example.toml config.toml
```

不要把真实 API Key、远端 Runtime Agent Key 或服务器密码提交到仓库。

### 2. 安装并构建前端

```bash
pnpm install
pnpm run build
```

### 3. 启动完整演示环境

```bash
docker compose up -d --build
```

只重建平台后端和前端：

```bash
docker compose up -d --build hub-api hub-ui
```

常用地址：

- 前台页面：http://127.0.0.1:28080
- 后端 API：http://127.0.0.1:48888
- API 文档：http://127.0.0.1:48888/docs
- LakeFS：http://127.0.0.1:28000
- MinIO 控制台：http://127.0.0.1:29000
- Meilisearch：http://127.0.0.1:27700
- MLflow：http://127.0.0.1:25000

## 演示数据

- 演示账号：`mai_lin`
- 演示密码：`CnModelHub123!`
- Meilisearch Key：`dev-meili-master-key`
- MinIO：`minioadmin / minioadmin`
- 演示模型：`qwen_demo/qwen2.5-0.5b-instruct`
- 演示数据集：`c-eval`
- 演示 Space：Qwen2.5 对话 Demo
- 快速评测：C-Eval 20 题
- 排行榜：生成式大语言模型排行榜

## 远端 GPU 部署与调用

项目支持把模型 Demo 和快速评测从本地机器迁移到远端 GPU。平台本地服务负责用户权限、仓库文件和页面展示；远端 GPU 只负责接收运行包、启动模型进程、提供状态/日志/代理接口。

### 1. 远端服务器

远端 GPU 是可选执行环境。部署时需要准备一台可通过 SSH 访问、已安装 Python/PyTorch/CUDA 运行环境的服务器，并为 Runtime Agent 配置可访问的 HTTPS Base URL。

健康检查：

```bash
curl "$CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_BASE_URL/health"
```

### 2. 部署 Runtime Agent

把 agent 脚本上传到远端：

```bash
ssh <ssh-alias> "mkdir -p <remote-agent-dir>"
scp scripts/remote_runtime_agent.py <ssh-alias>:<remote-agent-dir>/server.py
```

在远端启动服务：

```bash
cd <remote-agent-dir>
export RUNTIME_AGENT_API_KEY="<runtime-agent-key>"
export CN_MODEL_HUB_RUNTIME_ROOT=<remote-runtime-root>
export CN_MODEL_HUB_RUNTIME_SKIP_TORCH_INSTALL=true
nohup python -m uvicorn server:app <uvicorn-listen-options> > server.log 2>&1 &
echo $! > server.pid
```

查看日志：

```bash
ssh <ssh-alias> "tail -n 80 <remote-agent-dir>/server.log"
```

### 3. 本地平台启用远端 GPU

在本地 `.env.dev` 或部署环境变量中配置：

```bash
CN_MODEL_HUB_SPACE_RUNTIME_BACKEND=remote
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_BASE_URL=<runtime-agent-base-url>
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_API_KEY=<runtime-agent-key>
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_UPLOAD_METHOD=ssh
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_SSH_ALIAS=<ssh-alias>
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_ROOT=<remote-runtime-root>
```

然后重启后端：

```bash
docker compose up -d --force-recreate hub-api
```

启用后，模型仓库页的“运行”和快速评测会通过本地后端打包仓库文件、SSH 上传到远端 GPU，再由 Runtime Agent 启动 Gradio 或评测任务。

## 智能助手配置

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

如果需要调用外部大模型整理答案，通过环境变量注入密钥：

```bash
CN_MODEL_HUB_ASSISTANT_LLM_API_KEY=<your-api-key>
CN_MODEL_HUB_ASSISTANT_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CN_MODEL_HUB_ASSISTANT_LLM_MODEL=qwen3.7-max
```

没有配置 API Key 时，助手仍会返回本地检索整理结果。

## 常用维护命令

重建站内搜索索引：

```bash
curl -X POST http://127.0.0.1:48888/api/search/index/rebuild \
  -H "Authorization: Bearer <your-token>"
```

查看索引状态：

```bash
curl http://127.0.0.1:48888/api/search/index/status
```

运行后端测试：

```bash
python -m pytest
```

运行前端测试：

```bash
pnpm test
```
