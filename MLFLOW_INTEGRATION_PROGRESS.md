# MLflow Integration Progress

## 已完成内容

### 1. 仓库级 MLflow 绑定能力

- 后端新增了 repository 级别的 MLflow 绑定字段：
  - `mlflow_enabled`
  - `mlflow_experiment_name`
  - `mlflow_experiment_id`
  - `mlflow_last_synced_at`
- 新增数据库迁移：
  - `scripts/db_migrations/017_repository_mlflow_binding.py`
- 新增/补全了仓库级 MLflow API：
  - 读取绑定信息
  - 绑定 experiment
  - 解绑 experiment
  - 列出最近 runs
- 仓库详情接口已返回 MLflow 绑定信息。
- Space 运行时环境已注入 MLflow 相关环境变量，便于运行中的任务直接上报到绑定的 experiment。

### 2. 前端接入 MLflow 面板

- 新增仓库侧边栏面板 `RepoMlflowPanel.vue`
- 前端 API 客户端新增：
  - `getBinding`
  - `bind`
  - `unbind`
  - `listRuns`
- `RepoViewer.vue` 已接入 MLflow 面板展示与交互。

### 3. 测试补全与修复

- 新增前端测试：
  - `test/kohaku-hub-ui/components/test_repo_mlflow_panel.test.js`
- 修复并补齐多处前端测试，使其对齐当前中文 UI 文案和 `RepoViewer` 实际行为。
- `RepoViewer` 相关路径测试已恢复稳定并通过。
- 前端全量 `vitest` 已通过。

### 4. 后端测试准备

- 新增后端测试文件：
  - `test/kohakuhub/api/test_mlflow.py`
- 已使用 Anaconda `minimind` 环境尝试执行后端 MLflow 测试。

## 已完成验证

### 前端

已通过：

- `node_modules\\.bin\\vitest.CMD run --config vitest.config.js --configLoader runner --coverage.enabled=false`

结果：前端全量测试通过。

### 后端

已执行：

- `D:\\anaconda\\envs\\minimind\\python.exe -m pytest test\\kohakuhub\\api\\test_mlflow.py -q`

当前结果不是代码断言失败，而是基础依赖服务未启动。

## 当前阻塞

后端 MLflow 集成测试依赖以下本地服务：

- PostgreSQL `127.0.0.1:25432`
- MinIO `127.0.0.1:29001`
- LakeFS `127.0.0.1:28000`

这些服务原本应通过 `scripts/dev/up_infra.sh` 使用 Docker 拉起，但当前机器无法启动 Docker Desktop，原因是：

- 未检测到可用 virtualization support

因此当前无法完成 service-backed 后端测试。

## 下一步要做什么

1. 先解决本机虚拟化 / Docker Desktop 启动问题
2. 启动本地基础服务：
   - PostgreSQL
   - MinIO
   - LakeFS
3. 重新运行：
   - `bash scripts/dev/up_infra.sh`
   - `D:\\anaconda\\envs\\minimind\\python.exe -m pytest test\\kohakuhub\\api\\test_mlflow.py -q`
4. 若真实服务仍不可用，则补一套不依赖 Docker 的后端 mock/fake 测试，继续提高 MLflow 绑定逻辑覆盖率

## 本次提交范围

包含：

- MLflow 仓库级绑定后端实现
- MLflow 前端面板接入
- 相关前端测试修复与补全
- 后端 MLflow 测试文件
- 本进展说明文档

不包含：

- `.pytest_deps/` 本地依赖目录
