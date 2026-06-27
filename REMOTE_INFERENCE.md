# 远程 GPU 推理运行时说明

本项目支持把模型 Demo 和快速评测从本地机器切换到远程 GPU 执行。远程 GPU 只作为运行时执行面使用；用户、权限、仓库文件、数据库、对象存储和页面展示仍由本地 `cn_model_hub` 服务负责。

## 架构

```text
浏览器
  |
  v
cn_model_hub 前端
  |
  v
cn_model_hub 后端
  - 登录与权限
  - 仓库文件管理
  - LakeFS/OSS 访问
  - Runtime 状态聚合
  - Runtime Proxy 转发
  |
  | SSH 上传运行包
  | HTTPS 调用 Runtime Agent
  v
远程 GPU Runtime Agent
  - 接收 start/stop/status/logs/proxy 请求
  - 管理远程运行目录
  - 创建运行环境
  - 启动 app.py 或内置模型 Demo
  - 使用 CUDA 执行推理或评测
```

## 本地配置

默认配置仍使用本地运行时：

```toml
[app]
space_runtime_backend = "local"
```

需要启用远程 GPU 时，将以下值通过本地环境变量或部署配置注入：

```bash
CN_MODEL_HUB_SPACE_RUNTIME_BACKEND=remote
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_BASE_URL=<runtime-agent-base-url>
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_API_KEY=<runtime-agent-key>
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_UPLOAD_METHOD=ssh
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_SSH_ALIAS=<ssh-alias>
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_ROOT=<remote-runtime-root>
```

不要把真实服务器地址、端口、密钥或 SSH 凭据提交到仓库。

## Runtime Agent

远程服务器需要能通过 SSH 接收运行包，并通过 HTTPS 暴露 Runtime Agent。Agent 脚本位于：

```text
scripts/remote_runtime_agent.py
```

部署步骤示例：

```bash
ssh <ssh-alias> "mkdir -p <remote-agent-dir>"
scp scripts/remote_runtime_agent.py <ssh-alias>:<remote-agent-dir>/server.py
```

在远程服务器上启动：

```bash
cd <remote-agent-dir>
export RUNTIME_AGENT_API_KEY=<runtime-agent-key>
export CN_MODEL_HUB_RUNTIME_ROOT=<remote-runtime-root>
export CN_MODEL_HUB_RUNTIME_SKIP_TORCH_INSTALL=true
nohup python -m uvicorn server:app <uvicorn-listen-options> > server.log 2>&1 &
echo $! > server.pid
```

健康检查使用配置中的 Runtime Agent Base URL：

```bash
curl "$CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_BASE_URL/health"
```

## 调用流程

用户在模型仓库页点击“运行”后：

1. 本地后端完成用户权限校验。
2. 本地后端从 LakeFS/对象存储同步仓库文件。
3. 本地后端打包当前仓库版本。
4. 本地后端通过 SSH 上传运行包到远程 GPU。
5. 本地后端调用 Runtime Agent 的启动接口。
6. Runtime Agent 解包、准备环境并启动 Gradio 或仓库自带 `app.py`。
7. 前端通过本地后端的 runtime proxy 访问远程 Demo。

快速评测启用远程模式时也走同一套运行包上传和 Runtime Agent 调用链路。

## 安全约束

- Runtime Agent API Key 只能通过环境变量或服务器侧密钥管理注入。
- 远程 GPU 不直接访问本地数据库。
- 远程 GPU 不直接访问本地对象存储。
- 运行包由本地后端在完成权限校验后上传。
- 远程运行目录应放在容量充足的数据盘或临时盘，不应写入系统盘。
