<script setup>
const knowledgeDocs = [
  {
    title: "平台概览",
    description: "当前演示资源、核心页面和平台定位。",
    path: "/docs/platform-knowledge/overview",
    icon: "i-carbon-home",
  },
  {
    title: "模型和数据集",
    description: "模型仓库、模型卡片、数据集仓库和 C-Eval 展示。",
    path: "/docs/platform-knowledge/models-and-datasets",
    icon: "i-carbon-machine-learning-model",
  },
  {
    title: "Space 和在线 Demo",
    description: "Qwen2.5 本地模型推理 Demo 的运行方式。",
    path: "/docs/platform-knowledge/spaces-and-demo",
    icon: "i-carbon-application-web",
  },
  {
    title: "快速评测和排行榜",
    description: "C-Eval 20 题快速评测和生成式大语言模型排行榜。",
    path: "/docs/platform-knowledge/evaluation-and-leaderboard",
    icon: "i-carbon-trophy",
  },
  {
    title: "MLflow 和 LakeFS",
    description: "实验追踪与版本化对象存储的作用。",
    path: "/docs/platform-knowledge/mlflow-and-lakefs",
    icon: "i-carbon-flow",
  },
  {
    title: "搜索和智能助手",
    description: "Meilisearch、RAG 知识库和大模型整理链路。",
    path: "/docs/platform-knowledge/search-and-assistant",
    icon: "i-carbon-ai-results",
  },
  {
    title: "部署和演示账号",
    description: "Docker Compose 地址、账号和本地环境变量。",
    path: "/docs/platform-knowledge/deployment-and-accounts",
    icon: "i-carbon-container-services",
  },
];
</script>

<template>
  <div class="container-main py-12">
    <div class="mx-auto max-w-6xl">
      <div class="mb-8">
        <div class="stat-chip mb-4">
          <div class="i-carbon-document" />
          平台知识库
        </div>
        <h1 class="text-4xl font-bold">中文开源AI模型社区知识库</h1>
        <p class="mt-3 max-w-3xl text-lg text-slate-600 dark:text-slate-400">
          这里存放平台真实功能说明，也是智能助手唯一索引的 RAG 文档来源。
        </p>
      </div>

      <div class="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        <RouterLink
          v-for="doc in knowledgeDocs"
          :key="doc.path"
          :to="doc.path"
          class="card p-5 transition hover:-translate-y-0.5 hover:shadow-lg"
        >
          <div class="mb-4 flex items-center gap-3">
            <div :class="doc.icon" class="text-3xl text-blue-600 dark:text-blue-400" />
            <h2 class="text-xl font-semibold">{{ doc.title }}</h2>
          </div>
          <p class="text-sm leading-6 text-slate-600 dark:text-slate-400">
            {{ doc.description }}
          </p>
        </RouterLink>
      </div>
    </div>
  </div>
</template>
