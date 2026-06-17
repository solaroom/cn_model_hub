# 远程 GPU 推理运行时迁移计划

## 1. 背景与目标

当前项目的模型/Space 在线 Demo 由本地后端直接启动。实现位于 `src/cn_model_hub/api/space_runtime.py`：

- 本地后端从 LakeFS/OSS 取出仓库文件。
- 解压到本机 `.space-runtimes`。
- 创建 Python venv。
- 安装 `requirements.txt`。
- 启动 `app.py` 或内置 Qwen 本地模型模板。
- 前端通过 `/runtime/proxy` iframe 访问本地 Gradio 应用。

这套方案适合本机有 CPU/GPU 的场景，但当前开发机没有 GPU，用户上传模型后无法在本地完成 CUDA 推理。

本计划的目标是：**保留本地 cn_model_hub 作为控制面，把模型 Demo 的实际运行进程迁移到远程 GPU 服务器**。

不迁移的内容：

- 数据库不迁移到公网。
- LakeFS/MinIO/OSS 不迁移到公网。
- 用户权限、仓库管理、文件提交仍由本地主站负责。
- 站内 assistant 使用第三方 API 的逻辑不在本次范围内。

迁移的内容：

- 用户点击“启动运行”后，模型仓库文件打包发送到远程 GPU。
- 远程 GPU 负责创建运行环境、加载模型、启动 Gradio/app.py。
- 本地后端继续向前端提供原有 runtime API，并把 iframe/proxy 流量转发到远程 GPU runtime agent。

## 2. 总体架构

```text
浏览器
  |
  v
cn_model_hub 前端
  |
  v
本地 cn_model_hub 后端
  - 登录与权限
  - 仓库文件管理
  - LakeFS/OSS 访问
  - runtime 状态聚合
  - runtime proxy 转发
  |
  | SSH/SCP 上传运行包
  | HTTPS 调用 runtime agent
  v
远程 GPU Runtime Agent
  - 接收启动/停止/status/logs/proxy 请求
  - 管理远程缓存目录
  - 创建 venv/conda 环境
  - 启动 app.py/Gradio
  - 使用 CUDA 加载模型
```

核心原则：

- 本地后端是控制面。
- 远程 GPU 是执行面。
- 远程 GPU 不直接访问本地数据库。
- 远程 GPU 不直接访问本地 OSS。
- 模型文件由本地后端在完成权限校验后打包上传。

## 3. 远程服务器环境

当前可用远程 GPU 服务器：

```powershell
ssh seeta
```

建议运行目录：

```text
/root/autodl-tmp/cn-model-hub-runtime-agent
/root/autodl-tmp/cn-model-hub-runtimes
```

不要把运行包、模型权重、venv 放到根文件系统。根文件系统空间有限，应统一放在 `/root/autodl-tmp`。

远程 agent 可监听：

```text
0.0.0.0:6008
```

SeetaCloud 当前端口映射：

```text
127.0.0.1:6008 -> https://uu866823-86b2-6cbcbbb3.westb.seetacloud.com:8443/
```

端口 `6008` 运行独立的 Runtime Agent，提供以下路径：

```text
/api/runtime/start
/api/runtime/stop
/api/runtime/status/{runtime_key}
/api/runtime/logs/{runtime_key}
/api/runtime/proxy/{runtime_key}/{path:path}
```

## 4. 本地后端配置

建议新增配置项：

```toml
[app]
space_runtime_backend = "local"  # local | remote
space_runtime_remote_base_url = "https://uu866823-86b2-6cbcbbb3.westb.seetacloud.com:8443"
space_runtime_remote_api_key = ""
space_runtime_remote_upload_method = "ssh"
space_runtime_remote_ssh_alias = "seeta"
space_runtime_remote_root = "/root/autodl-tmp/cn-model-hub-runtimes"
```

对应环境变量：

```powershell
CN_MODEL_HUB_SPACE_RUNTIME_BACKEND=remote
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_BASE_URL=https://uu866823-86b2-6cbcbbb3.westb.seetacloud.com:8443
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_API_KEY=<runtime-agent-key>
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_UPLOAD_METHOD=ssh
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_SSH_ALIAS=seeta
CN_MODEL_HUB_SPACE_RUNTIME_REMOTE_ROOT=/root/autodl-tmp/cn-model-hub-runtimes
```

`space_runtime_backend = "local"` 时保留现有行为，方便无远程 GPU 时继续用本地 CPU 调试。

## 5. 远程 Runtime Agent API

### 5.1 健康检查

```http
GET /health
```

返回：

```json
{
  "status": "ok",
  "cuda_available": true,
  "gpu": "NVIDIA GeForce RTX 4090",
  "active_runtime_key": "model-qwen_demo-qwen2.5-0.5b"
}
```

### 5.2 启动 runtime

```http
POST /api/runtime/start
Authorization: Bearer <runtime-agent-key>
Content-Type: application/json
```

请求：

```json
{
  "runtime_key": "model-qwen_demo-qwen2.5-0.5b",
  "repo_type": "model",
  "repo_id": "qwen_demo/qwen2.5-0.5b",
  "revision": "main",
  "commit_id": "abc123",
  "remote_root": "/root/autodl-tmp/cn-model-hub-runtimes",
  "app_entry": "app.py",
  "using_builtin_model_app": true,
  "install_requirements": true,
  "env": {
    "LOCAL_MODEL_PATH": "/root/autodl-tmp/cn-model-hub-runtimes/model-qwen_demo-qwen2.5-0.5b/current",
    "MAX_NEW_TOKENS": "256"
  }
}
```

返回：

```json
{
  "status": "running",
  "runtime_key": "model-qwen_demo-qwen2.5-0.5b",
  "commit_id": "abc123",
  "message": "Runtime is running.",
  "proxy_url": "/api/runtime/proxy/model-qwen_demo-qwen2.5-0.5b/"
}
```

### 5.3 停止 runtime

```http
POST /api/runtime/stop
Authorization: Bearer <runtime-agent-key>
Content-Type: application/json
```

请求：

```json
{
  "runtime_key": "model-qwen_demo-qwen2.5-0.5b",
  "reason": "repository updated"
}
```

返回：

```json
{
  "status": "stopped",
  "runtime_key": "model-qwen_demo-qwen2.5-0.5b",
  "message": "Runtime stopped: repository updated."
}
```

### 5.4 查询状态

```http
GET /api/runtime/status/{runtime_key}
Authorization: Bearer <runtime-agent-key>
```

返回：

```json
{
  "status": "running",
  "runtime_key": "model-qwen_demo-qwen2.5-0.5b",
  "repo_id": "qwen_demo/qwen2.5-0.5b",
  "commit_id": "abc123",
  "pid": 12345,
  "port": 7861,
  "message": "Runtime is running.",
  "logs": []
}
```

### 5.5 代理 Gradio/app.py

```http
ANY /api/runtime/proxy/{runtime_key}/{path:path}
Authorization: Bearer <runtime-agent-key>
```

远程 agent 将该请求转发到内部 Gradio 进程：

```text
http://127.0.0.1:{runtime_port}/{path}
```

本地 cn_model_hub 不直接暴露远程 Gradio 动态端口，只代理到远程 agent 的 `/api/runtime/proxy/...`。

## 6. 运行包发送方案

MVP 使用 `tar.gz + scp/ssh`。

启动模型时：

1. 本地后端校验用户对仓库的写权限。
2. 本地后端解析 revision 对应的 `commit_id`。
3. 本地后端调用现有 `_materialize_repo()`，把仓库文件解到本地 `.space-runtimes`。
4. 本地后端生成运行包 `source.tar.gz`。
5. 本地后端通过 `ssh seeta` 创建远程目录。
6. 本地后端通过 `scp` 上传运行包到远程 `incoming/source.tar.gz`。
7. 远程 agent 解压并原子替换 `current`。
8. 本地后端调用远程 agent `/api/runtime/start`。

示例命令：

```powershell
tar -czf .space-runtimes/runtime.tar.gz -C .space-runtimes/model-qwen_demo-qwen2.5-0.5b .
ssh seeta "mkdir -p /root/autodl-tmp/cn-model-hub-runtimes/model-qwen_demo-qwen2.5-0.5b/incoming"
scp .space-runtimes/runtime.tar.gz seeta:/root/autodl-tmp/cn-model-hub-runtimes/model-qwen_demo-qwen2.5-0.5b/incoming/source.tar.gz
```

生产化后可改为 `rsync`，减少重复上传。但 Windows 本地环境下 `tar.gz + scp` 实现成本更低。

## 7. 远程缓存目录策略

由于远程服务器磁盘有限，采用 **每个仓库只保留一个缓存目录** 的策略。

目录结构：

```text
/root/autodl-tmp/cn-model-hub-runtimes/
  model-qwen_demo-qwen2.5-0.5b/
    current/
    incoming/
    logs/
    venv/
    .commit
```

说明：

- `current/` 是当前可运行的仓库文件。
- `incoming/` 是新上传包的临时解压目录。
- `.commit` 记录 `current/` 对应的 commit id。
- `logs/` 保存 runtime stdout/stderr。
- `venv/` 保存该仓库 runtime Python 环境。

更新规则：

1. 本地后端启动前解析最新 `commit_id`。
2. 远程 agent 读取 `.commit`。
3. 如果 `.commit == latest_commit_id`，跳过上传和解压，直接启动。
4. 如果 commit 不一致：
   - 停止该仓库旧 runtime。
   - 清理旧 `incoming/`。
   - 上传新 `source.tar.gz`。
   - 解压到 `incoming/current/`。
   - 解压成功后删除旧 `current/`。
   - 将 `incoming/current/` 移动为新的 `current/`。
   - 写入新的 `.commit`。
   - 启动新的 `current/app.py`。

禁止直接覆盖 `current/`。必须通过 `incoming -> current` 替换，避免上传或解压失败时出现半新半旧的脏目录。

## 8. 并发与 GPU 调度策略

第一版按单卡 RTX 4090 设计：**同一时间只允许运行一个模型 runtime**。

规则：

- 同一仓库同一 commit：复用已有 runtime。
- 同一仓库新 commit：停止旧 runtime，替换缓存后启动新 runtime。
- 不同仓库：如果 GPU 已有 runtime 运行，则拒绝启动。
- 不做排队。
- 不做运行 30 分钟自动停止。
- 不做空闲 10 分钟自动停止。

不同仓库并发启动时，远程 agent 返回：

```json
{
  "status": "busy",
  "message": "GPU is busy. Current runtime: model-qwen_demo-qwen2.5-0.5b",
  "active_runtime_key": "model-qwen_demo-qwen2.5-0.5b"
}
```

本地后端将其转换为前端可读提示。

后续如需支持排队，可扩展：

```text
running 1 个
queued N 个
用户可取消 queued 任务
运行结束后自动启动队首任务
```

但 MVP 不做排队，避免引入任务一致性和取消逻辑。

## 9. 仓库文件变更时自动停止

不采用固定时间自动停止，改为 **仓库文件有改动时自动停止对应 runtime**。

触发规则：

```text
running_commit_id != latest_commit_id
```

或者仓库写操作成功后主动触发：

```python
stop_runtime_for_repo(repo_type, namespace, name, reason="repository updated")
```

需要接入的写操作路径包括：

- 文件上传成功。
- 文件编辑成功。
- 文件删除成功。
- commit 成功。
- branch reset 成功。
- branch merge 成功。
- branch revert 成功。
- LFS 上传完成且进入可见 commit。

建议做两层保护：

1. 写操作成功后主动停止 runtime。
2. `GET /runtime` 状态查询时兜底检查当前 runtime commit 是否仍等于最新 commit。

自动停止后的状态：

```json
{
  "status": "stopped",
  "message": "仓库文件已更新，旧运行时已自动停止，请重新启动。",
  "proxy_url": "",
  "commit_id": "old_commit"
}
```

远程缓存目录保留，但下次启动会根据 `.commit` 判断是否需要重新上传和替换 `current/`。

## 10. 本地代码改造计划

### 10.1 配置层

修改 `src/cn_model_hub/config.py`：

- 增加 `space_runtime_backend`。
- 增加远程 agent base URL。
- 增加远程 agent API key。
- 增加 SSH alias。
- 增加远程 root 目录。
- 增加环境变量解析。

同步修改：

- `config-example.toml`
- `.env.dev.example`
- `docker-compose.yml`

### 10.2 Runtime Driver 抽象

将 `space_runtime.py` 中的启动/停止/status/proxy 逻辑抽象为 driver：

```text
RuntimeDriver
  start(repo, revision, install_requirements)
  stop(repo, reason)
  status(repo)
  proxy(repo, request, path)

LocalRuntimeDriver
  保留当前本地进程实现

RemoteRuntimeDriver
  上传运行包
  调用远程 agent
  转发 proxy
```

第一版可先在 `space_runtime.py` 内部拆函数，不必立即拆多个文件。稳定后再整理为：

```text
src/cn_model_hub/api/runtime/
  __init__.py
  local.py
  remote.py
  types.py
```

### 10.3 RemoteRuntimeDriver 启动流程

伪代码：

```python
async def start_remote_runtime(repo, revision, install_requirements):
    workdir, commit_id = await _materialize_repo(repo, revision)
    runtime_key = build_runtime_key(repo)

    remote_status = await remote_agent_status(runtime_key)
    if remote_status.commit_id != commit_id:
        await remote_agent_stop(runtime_key, reason="repository updated")
        package = await create_runtime_tar(workdir)
        await upload_package(runtime_key, package)
        await remote_agent_prepare(runtime_key, commit_id)

    return await remote_agent_start(
        runtime_key=runtime_key,
        repo=repo,
        revision=revision,
        commit_id=commit_id,
        install_requirements=install_requirements,
    )
```

### 10.4 Proxy 转发

本地前端仍访问：

```text
/api/models/{namespace}/{name}/runtime/proxy/
```

本地后端根据 backend 转发：

```text
local:
  http://127.0.0.1:{local_port}/...

remote:
  {remote_base_url}/api/runtime/proxy/{runtime_key}/...
```

这样 `SpaceRuntimePanel.vue` 基本不用改。

### 10.5 Stop Hook

新增工具函数：

```python
async def stop_runtime_for_repo(
    repo_type: str,
    namespace: str,
    name: str,
    reason: str,
) -> None:
    ...
```

在仓库文件变更成功后调用。

如果调用远程 stop 失败，不应让文件提交失败，但要记录日志：

```text
Repository updated, but failed to stop remote runtime: ...
```

## 11. 远程 Agent 实现计划

远程 agent 建议使用 FastAPI。

文件结构：

```text
/root/autodl-tmp/cn-model-hub-runtime-agent/
  server.py
  start.sh
  runtime_key
  logs/
```

`server.py` 负责：

- 校验 bearer token。
- 维护内存中的 runtime 状态。
- 检查 GPU 是否忙。
- 创建/复用 venv。
- 安装依赖。
- 启动 `app.py`。
- 读取 stdout/stderr。
- 代理 Gradio 请求。
- 停止进程。

远程 agent 状态结构：

```python
runtimes = {
    runtime_key: {
        "status": "starting|running|stopped|error",
        "repo_id": "...",
        "commit_id": "...",
        "pid": 12345,
        "port": 7861,
        "process": process,
        "logs": deque(maxlen=5000),
    }
}

active_runtime_key = None
```

启动前检查：

- 是否已有其他 runtime running。
- `nvidia-smi` 是否可用。
- CUDA 是否可用。
- 远程目录 `.commit` 是否匹配。
- `current/` 是否存在。

## 12. 安全设计

远程 agent 必须启用 API key：

```text
Authorization: Bearer <runtime-agent-key>
```

key 存放：

```text
/root/autodl-tmp/cn-model-hub-runtime-agent/runtime_key
```

本地配置只通过环境变量注入，不提交仓库。

安全边界：

- 不把数据库暴露公网。
- 不把 MinIO/OSS 暴露公网。
- 不把 root 密码写入仓库。
- SSH 只用于上传运行包。
- HTTP API 只使用 runtime agent key 鉴权。
- 远程 agent 只信任本地主站传来的已授权运行包。

## 13. 测试计划

### 13.1 单模型启动

1. 上传或使用已有 Qwen 模型仓库。
2. 点击“启动”。
3. 本地生成运行包。
4. 远程收到 `source.tar.gz`。
5. 远程替换 `current/`。
6. 远程启动 Gradio。
7. 前端 iframe 可聊天。
8. 日志能显示 CUDA 可用。

### 13.2 同仓库重复启动

1. 第一次启动成功。
2. 第二次点击启动。
3. 不重复上传。
4. 复用当前 runtime。

### 13.3 仓库更新后启动

1. 修改 `app.py` 或模型文件。
2. commit 成功。
3. 当前 runtime 自动停止。
4. 再次点击启动。
5. 远程替换 `current/`。
6. `.commit` 更新为新 commit。

### 13.4 GPU 忙

1. 用户 A 启动模型 A。
2. 用户 B 启动模型 B。
3. 远程 agent 返回 busy。
4. 前端显示 GPU 忙提示。

### 13.5 上传失败

1. 中断 scp 或上传损坏包。
2. 远程不得破坏旧 `current/`。
3. `.commit` 不应更新。
4. runtime 状态返回 error。

## 14. 分阶段落地

### 阶段一：远程 Agent MVP

- 实现 `/health`。
- 实现 `/api/runtime/start`。
- 实现 `/api/runtime/stop`。
- 实现 `/api/runtime/status/{runtime_key}`。
- 实现 `/api/runtime/proxy/{runtime_key}/{path:path}`。
- 支持单 GPU 单 runtime。
- 支持每仓库单缓存目录。

### 阶段二：本地后端接入 remote backend

- 增加配置项。
- 增加 RemoteRuntimeDriver。
- 实现 tar.gz 打包。
- 实现 ssh/scp 上传。
- 实现本地 proxy 到远程 agent。
- 保留 local backend。

### 阶段三：仓库变更自动停止

- 增加 `stop_runtime_for_repo()`。
- 接入上传、编辑、删除、commit、merge、reset、revert 等写路径。
- 在 runtime status 中增加 commit 兜底检查。

### 阶段四：体验与稳定性

- 优化前端错误提示。
- 显示 GPU 忙状态。
- 显示远程 CUDA/GPU 信息。
- 增加启动日志。
- 增加远程 agent 启动脚本和运维文档。

## 15. 最终预期行为

用户在本地启动 cn_model_hub 后：

1. 上传模型仓库。
2. 进入模型页 runtime tab。
3. 点击启动。
4. 本地后端完成权限校验和运行包上传。
5. 远程 GPU 启动模型 Demo。
6. 前端 iframe 展示远程 GPU 上运行的 Gradio。
7. 如果仓库文件更新，旧 runtime 自动停止。
8. 再次启动时，远程缓存会被替换为最新 commit。
9. 如果另一个模型正在占用 GPU，新模型启动会被拒绝并提示 GPU 忙。

这个方案在不暴露数据库和 OSS 的前提下，把模型推理执行从本机迁移到远程 GPU，同时保留当前前端交互和仓库权限模型。
