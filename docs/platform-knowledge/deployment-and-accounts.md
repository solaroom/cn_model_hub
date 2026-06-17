# 部署和演示账号

项目支持 Docker Compose 本地演示部署。启动后可以访问前端、后端 API、MinIO、LakeFS、Meilisearch 和 MLflow。

## 本地启动

常用命令：

```bash
docker compose up -d --build
```

如果只重建平台服务：

```bash
docker compose up -d --build hub-api hub-ui
```

## 访问地址

- 前端首页：`http://127.0.0.1:28080`
- 后端 API：`http://127.0.0.1:48888`
- API 文档：`http://127.0.0.1:48888/docs`
- MinIO 控制台：`http://127.0.0.1:29000`
- LakeFS：`http://127.0.0.1:28000`
- Meilisearch：`http://127.0.0.1:27700`
- MLflow：`http://127.0.0.1:25000`

## 演示账号

- 用户名：`mai_lin`
- 密码：`CnModelHub123!`

## 大模型配置

不要把大模型 API Key 写入代码或 README。智能助手调用 LLM 整理答案，推荐在本机 shell 或 `.env.dev` 中配置。下面示例使用 DashScope 千问：

```bash
export CN_MODEL_HUB_ASSISTANT_LLM_API_KEY="你的 DashScope API Key"
export CN_MODEL_HUB_ASSISTANT_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export CN_MODEL_HUB_ASSISTANT_LLM_MODEL=qwen3.7-max
docker compose up -d --force-recreate hub-api
```

配置后，智能助手会调用配置的大模型进行最终答案整理；未配置时，平台会用本地检索结果生成兜底回答。
