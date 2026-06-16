<template>
  <div class="page-shell">
    <section class="container-main">
      <div
        class="relative overflow-hidden rounded-lg px-6 py-10 text-white shadow-2xl md:px-10 md:py-14"
        :style="{ background: 'var(--kh-hero)' }"
      >
        <div class="pointer-events-none absolute inset-0 opacity-22">
          <div class="absolute inset-x-0 top-0 h-px bg-white/55" />
          <div class="absolute right-0 top-0 h-full w-2/5 bg-[linear-gradient(135deg,rgba(255,255,255,0.18)_0,rgba(255,255,255,0)_55%)]" />
          <div class="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.08)_1px,transparent_1px)] bg-[size:32px_32px]" />
        </div>

        <div class="relative grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
          <div class="max-w-3xl">
            <div class="stat-chip !mb-4 !bg-white/12 !text-white">
              <div class="i-carbon-ai-results" />
              中文开源AI模型社区
            </div>
            <h1 class="max-w-3xl text-3xl font-bold leading-tight md:text-5xl">
              中文开源AI模型社区：面向中文模型的开源展示平台。
            </h1>
            <p class="mt-4 max-w-2xl text-base text-white/82 md:text-lg">
              围绕中文大模型、语料数据集、在线 Demo 和评测榜单汇集资源，
              帮助同学和开发者更方便地上传、检索、复现与讨论开源 AI 项目。
            </p>

            <div class="mt-7 flex flex-wrap gap-3">
              <el-button
                size="large"
                round
                class="!border-white/0 !bg-white !px-6 !text-slate-900 hover:!bg-slate-100"
                @click="$router.push('/models')"
              >
                浏览开源模型
              </el-button>
              <el-button
                size="large"
                round
                class="!border-white/35 !bg-white/8 !px-6 !text-white hover:!bg-white/14"
                @click="$router.push('/spaces')"
              >
                体验在线 Demo
              </el-button>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <div class="rounded-lg border border-white/14 bg-white/10 p-4 backdrop-blur">
              <div class="flex items-center gap-2 text-sm text-white/70">
                <div class="i-carbon-machine-learning-model" />
                模型托管
              </div>
              <div class="mt-2 text-3xl font-semibold">{{ stats.models }}</div>
            </div>
            <div class="rounded-lg border border-white/14 bg-white/10 p-4 backdrop-blur">
              <div class="flex items-center gap-2 text-sm text-white/70">
                <div class="i-carbon-data-table" />
                中文数据集
              </div>
              <div class="mt-2 text-3xl font-semibold">{{ stats.datasets }}</div>
            </div>
            <div class="rounded-lg border border-white/14 bg-white/10 p-4 backdrop-blur">
              <div class="flex items-center gap-2 text-sm text-white/70">
                <div class="i-carbon-application-web" />
                在线 Demo
              </div>
              <div class="mt-2 text-3xl font-semibold">{{ stats.spaces }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="container-main mt-10">
      <div class="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h2 class="section-title">生成式大语言模型排行榜</h2>
          <p class="section-subtitle mt-2">C-Eval 20题准确率 · 前十名</p>
        </div>
        <el-button round @click="$router.push('/leaderboards/generative-llm')">
          <div class="i-carbon-trophy mr-1 inline-block" />
          查看完整排行榜
        </el-button>
      </div>

      <div class="card">
        <div v-if="leaderboardLoading" class="py-10 text-center text-slate-500 dark:text-slate-400">
          <el-icon class="is-loading" :size="32">
            <div class="i-carbon-loading" />
          </el-icon>
        </div>
        <div v-else-if="topLeaderboardEntries.length === 0" class="py-10 text-center text-slate-500 dark:text-slate-400">
          暂无完成评测的模型
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead class="border-b border-slate-200 text-left text-slate-500 dark:border-slate-700 dark:text-slate-400">
              <tr>
                <th class="py-3 pr-4 font-medium">排名</th>
                <th class="py-3 pr-4 font-medium">模型</th>
                <th class="py-3 pr-4 font-medium">类型</th>
                <th class="py-3 pr-4 font-medium">正确数</th>
                <th class="py-3 pr-4 font-medium">准确率</th>
                <th class="py-3 pr-4 font-medium">提交</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="entry in topLeaderboardEntries"
                :key="entry.id"
                class="border-b border-slate-100 last:border-0 dark:border-slate-800"
              >
                <td class="py-3 pr-4 font-semibold">#{{ entry.rank }}</td>
                <td class="py-3 pr-4">
                  <RouterLink
                    :to="`/models/${entry.repository.namespace}/${entry.repository.name}?tab=evaluations`"
                    class="font-medium text-blue-600 hover:underline dark:text-blue-400"
                  >
                    {{ entry.repository.full_id }}
                  </RouterLink>
                </td>
                <td class="py-3 pr-4">{{ entry.model_family }}</td>
                <td class="py-3 pr-4">{{ entry.correct }} / {{ entry.total }}</td>
                <td class="py-3 pr-4 font-semibold">{{ formatAccuracy(entry.accuracy) }}</td>
                <td class="py-3 pr-4 font-mono text-xs">
                  {{ entry.commit_id ? entry.commit_id.slice(0, 7) : "-" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="container-main mt-10">
      <div class="mb-6 flex flex-col gap-4 md:flex-row md:items-end">
        <div>
          <h2 class="section-title">{{ repoSectionTitle }}</h2>
          <p class="section-subtitle mt-2">
            按模型、数据集和在线 Demo 分区展示资源，方便快速发现可复现项目。
          </p>
        </div>

        <div class="glass-toolbar rounded-lg p-3 md:ml-auto md:w-80">
          <el-select
            v-model="selectedSort"
            placeholder="选择排序方式"
            class="w-full"
          >
            <el-option label="趋势优先" value="trending" />
            <el-option label="最近创建" value="recent" />
            <el-option label="最近更新" value="updated" />
            <el-option label="下载最多" value="downloads" />
            <el-option label="点赞最多" value="likes" />
          </el-select>
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-3">
        <section class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="i-carbon-model text-2xl text-blue-500" />
              <h3 class="text-xl font-semibold">模型</h3>
            </div>
            <div class="stat-chip">{{ stats.models }}</div>
          </div>
          <div class="space-y-3">
            <article
              v-for="repo in recentModels"
              :key="repo.id"
              class="card repo-card cursor-pointer"
              @click="goToRepo('model', repo)"
            >
              <div class="flex items-start gap-3">
                <div
                  class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-500 dark:bg-blue-950/35 dark:text-blue-300"
                >
                  <div class="i-carbon-model text-xl" />
                </div>
                <div class="min-w-0 flex-1">
                  <RouterLink
                    :to="getRepoPath('model', repo)"
                    class="block truncate font-semibold text-slate-900 hover:text-blue-600 dark:text-slate-100 dark:hover:text-blue-300"
                    @click.stop
                  >
                    {{ repo.id }}
                  </RouterLink>
                  <div class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {{ formatDate(repo.lastModified) }}
                  </div>
                  <div class="mt-3 flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                    <span class="flex items-center gap-1">
                      <div class="i-carbon-download" />
                      {{ repo.downloads || 0 }}
                    </span>
                    <span class="flex items-center gap-1">
                      <div class="i-carbon-favorite" />
                      {{ repo.likes || 0 }}
                    </span>
                  </div>
                </div>
              </div>
            </article>
            <el-button round class="w-full" @click="$router.push('/models')">
              查看全部模型
            </el-button>
          </div>
        </section>

        <section class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="i-carbon-data-table text-2xl text-emerald-500" />
              <h3 class="text-xl font-semibold">数据集</h3>
            </div>
            <div class="stat-chip">{{ stats.datasets }}</div>
          </div>
          <div class="space-y-3">
            <article
              v-for="repo in recentDatasets"
              :key="repo.id"
              class="card repo-card cursor-pointer"
              @click="goToRepo('dataset', repo)"
            >
              <div class="flex items-start gap-3">
                <div
                  class="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-500 dark:bg-emerald-950/35 dark:text-emerald-300"
                >
                  <div class="i-carbon-data-table text-xl" />
                </div>
                <div class="min-w-0 flex-1">
                  <RouterLink
                    :to="getRepoPath('dataset', repo)"
                    class="block truncate font-semibold text-slate-900 hover:text-emerald-600 dark:text-slate-100 dark:hover:text-emerald-300"
                    @click.stop
                  >
                    {{ displayRepoName('dataset', repo) }}
                  </RouterLink>
                  <div class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {{ formatDate(repo.lastModified) }}
                  </div>
                  <div class="mt-3 flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                    <span class="flex items-center gap-1">
                      <div class="i-carbon-download" />
                      {{ repo.downloads || 0 }}
                    </span>
                    <span class="flex items-center gap-1">
                      <div class="i-carbon-favorite" />
                      {{ repo.likes || 0 }}
                    </span>
                  </div>
                </div>
              </div>
            </article>
            <el-button round class="w-full" @click="$router.push('/datasets')">
              查看全部数据集
            </el-button>
          </div>
        </section>

        <section class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="i-carbon-application text-2xl text-violet-500" />
              <h3 class="text-xl font-semibold">空间</h3>
            </div>
            <div class="stat-chip">{{ stats.spaces }}</div>
          </div>
          <div class="space-y-3">
            <article
              v-for="repo in recentSpaces"
              :key="repo.id"
              class="card repo-card cursor-pointer"
              @click="goToDemo(repo)"
            >
              <div class="flex items-start gap-3">
                <div
                  class="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-50 text-violet-500 dark:bg-violet-950/35 dark:text-violet-300"
                >
                  <div class="i-carbon-application text-xl" />
                </div>
                <div class="min-w-0 flex-1">
                  <RouterLink
                    :to="getDemoPath(repo)"
                    class="block truncate font-semibold text-slate-900 hover:text-violet-600 dark:text-slate-100 dark:hover:text-violet-300"
                    @click.stop
                  >
                    {{ repo.full_id || repo.id }}
                  </RouterLink>
                  <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                    <el-tag size="small" effect="plain">
                      {{ repo.demo_label || "Demo" }}
                    </el-tag>
                    <el-tag size="small" :type="demoStatusType(repo.status)">
                      {{ demoStatusLabel(repo.status) }}
                    </el-tag>
                    <span>{{ formatDate(repo.last_modified || repo.lastModified) }}</span>
                  </div>
                  <div class="mt-3 flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                    <span class="flex items-center gap-1">
                      <div class="i-carbon-download" />
                      {{ repo.downloads || 0 }}
                    </span>
                    <span class="flex items-center gap-1">
                      <div class="i-carbon-favorite" />
                      {{ repo.likes || 0 }}
                    </span>
                  </div>
                </div>
              </div>
            </article>
            <el-button round class="w-full" @click="$router.push('/spaces')">
              查看全部空间
            </el-button>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup>
import { evaluationAPI, repoAPI, runtimeAPI } from "@/utils/api";
import { formatRelativeTime } from "@/utils/datetime";
import {
  getRepoSortPreference,
  setRepoSortPreference,
} from "@/utils/repoSortPreference";
import { ElMessage } from "element-plus";

const router = useRouter();
const route = useRoute();

const stats = ref({ models: 0, datasets: 0, spaces: 0 });
const recentModels = ref([]);
const recentDatasets = ref([]);
const recentSpaces = ref([]);
const leaderboardEntries = ref([]);
const leaderboardLoading = ref(false);
const selectedSort = ref(
  getRepoSortPreference({
    scope: "home",
    repoType: "all",
    allowedValues: ["trending", "recent", "updated", "downloads", "likes"],
    fallback: "trending",
  }),
);

const repoSectionTitle = computed(() => {
  switch (selectedSort.value) {
    case "recent":
      return "最新创建";
    case "updated":
      return "最近更新";
    case "downloads":
      return "下载热榜";
    case "likes":
      return "点赞热榜";
    default:
      return "社区精选";
  }
});

const topLeaderboardEntries = computed(() => leaderboardEntries.value.slice(0, 10));

function formatDate(date) {
  return formatRelativeTime(date, "never");
}

function formatAccuracy(value) {
  if (value === null || value === undefined) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

function getRepoPath(type, repo) {
  const [namespace, name] = repo.id.split("/");
  return `/${type}s/${namespace}/${name}`;
}

function getDemoPath(repo) {
  if (repo.detail_url) return repo.detail_url;
  return getRepoPath(repo.repo_type || "space", repo);
}

function displayRepoName(type, repo) {
  if (type !== "dataset") return repo.id;
  return repo.name || String(repo.id || "").split("/").pop();
}

function goToRepo(type, repo) {
  router.push(getRepoPath(type, repo));
}

function goToDemo(repo) {
  router.push(getDemoPath(repo));
}

function demoStatusLabel(status) {
  const labels = {
    running: "运行中",
    starting: "启动中",
    stopped: "未启动",
    error: "异常",
  };
  return labels[status] || "未启动";
}

function demoStatusType(status) {
  if (status === "running") return "success";
  if (status === "starting") return "warning";
  if (status === "error") return "danger";
  return "info";
}

async function loadStats() {
  try {
    const [models, datasets, demos] = await Promise.all([
      repoAPI.listRepos("model", {
        limit: 100,
        sort: selectedSort.value,
        fallback: false,
      }),
      repoAPI.listRepos("dataset", {
        limit: 100,
        sort: selectedSort.value,
        fallback: false,
      }),
      runtimeAPI.listDemos(),
    ]);

    stats.value = {
      models: models.data.length,
      datasets: datasets.data.length,
      spaces: demos.data.demos?.length || 0,
    };

    recentModels.value = models.data.slice(0, 3);
    recentDatasets.value = datasets.data.slice(0, 3);
    recentSpaces.value = (demos.data.demos || []).slice(0, 3);
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

async function loadLeaderboard() {
  leaderboardLoading.value = true;
  try {
    const { data } = await evaluationAPI.leaderboard("generative-llm");
    leaderboardEntries.value = data.entries || [];
  } catch (err) {
    console.error("Failed to load leaderboard:", err);
    leaderboardEntries.value = [];
  } finally {
    leaderboardLoading.value = false;
  }
}

watch(selectedSort, () => {
  setRepoSortPreference({
    scope: "home",
    repoType: "all",
    value: selectedSort.value,
  });
  loadStats();
});

onMounted(() => {
  if (route.query.error) {
    const errorType = route.query.error;
    const message = route.query.message || "发生错误";

    if (errorType === "invalid_token") {
      ElMessage.error(decodeURIComponent(message));
      router.replace("/");
    } else if (errorType === "user_not_found") {
      ElMessage.error("未找到对应用户账号");
      router.replace("/");
    }
  }

  loadStats();
  loadLeaderboard();
});
</script>
