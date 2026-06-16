<template>
  <div class="card">
    <div class="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
      <div>
        <h2 class="text-xl font-semibold">快速评测</h2>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          C-Eval · 20 题 · Qwen2.5
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <el-button
          type="primary"
          :loading="starting"
          :disabled="!isOwner || !supported || isRunning"
          @click="startEvaluation"
        >
          <div class="i-carbon-play mr-1 inline-block" />
          开始评测
        </el-button>
        <el-button @click="loadEvaluations">
          <div class="i-carbon-renew mr-1 inline-block" />
          刷新
        </el-button>
        <RouterLink to="/leaderboards/generative-llm">
          <el-button plain>
            <div class="i-carbon-trophy mr-1 inline-block" />
            排行榜
          </el-button>
        </RouterLink>
      </div>
    </div>

    <el-alert
      v-if="!isOwner"
      class="mb-4"
      title="只有仓库拥有者可以发起评测"
      type="info"
      :closable="false"
      show-icon
    />
    <el-alert
      v-if="loaded && !supported"
      class="mb-4"
      title="当前快速评测只支持 Qwen2.5 类型模型"
      type="warning"
      :closable="false"
      show-icon
    />
    <el-alert
      v-if="loaded && datasetAvailable"
      class="mb-4"
      :title="`C-Eval 20题数据已就绪：优先使用站内 ${datasetRepo}，缺失时使用项目内置 quick_eval 子集`"
      type="success"
      :closable="false"
      show-icon
    />

    <div v-if="loading" class="py-10 text-center text-gray-500 dark:text-gray-400">
      <el-icon class="is-loading" :size="32">
        <div class="i-carbon-loading" />
      </el-icon>
    </div>
    <div v-else-if="runs.length === 0" class="rounded border border-dashed border-gray-300 p-8 text-center text-gray-500 dark:border-gray-700 dark:text-gray-400">
      暂无评测记录
    </div>
    <div v-else class="space-y-4">
      <div
        v-for="run in runs"
        :key="run.id"
        class="rounded border border-gray-200 p-4 dark:border-gray-700"
      >
        <div class="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <el-tag :type="statusType(run.status)" effect="light">
                {{ statusLabel(run.status) }}
              </el-tag>
              <span class="text-sm text-gray-500 dark:text-gray-400">
                {{ run.benchmark }} / {{ run.leaderboard_label }}
              </span>
              <span v-if="run.commit_id" class="font-mono text-xs text-gray-500">
                {{ run.commit_id.slice(0, 7) }}
              </span>
            </div>
            <div v-if="run.error" class="mt-3 text-sm text-red-600 dark:text-red-400">
              {{ run.error }}
            </div>
          </div>
          <div class="text-left sm:text-right">
            <div class="text-2xl font-semibold">
              {{ formatAccuracy(run.accuracy) }}
            </div>
            <div class="text-sm text-gray-500 dark:text-gray-400">
              {{ run.correct }} / {{ run.total }}
            </div>
          </div>
        </div>
        <div v-if="run.result?.details?.length" class="mt-4 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead class="text-left text-gray-500 dark:text-gray-400">
              <tr>
                <th class="py-2 pr-4 font-medium">题目</th>
                <th class="py-2 pr-4 font-medium">科目</th>
                <th class="py-2 pr-4 font-medium">预测</th>
                <th class="py-2 pr-4 font-medium">答案</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="detail in run.result.details.slice(0, 5)"
                :key="detail.id"
                class="border-t border-gray-100 dark:border-gray-800"
              >
                <td class="py-2 pr-4 font-mono text-xs">{{ detail.id }}</td>
                <td class="py-2 pr-4">{{ detail.subject }}</td>
                <td
                  class="py-2 pr-4 font-semibold"
                  :class="detail.correct ? 'text-green-600' : 'text-red-600'"
                >
                  {{ detail.prediction || "-" }}
                </td>
                <td class="py-2 pr-4 font-semibold">{{ detail.answer }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ElMessage } from "element-plus";
import { evaluationAPI } from "@/utils/api";

const props = defineProps({
  repoType: { type: String, required: true },
  namespace: { type: String, required: true },
  name: { type: String, required: true },
  branch: { type: String, default: "main" },
  isOwner: { type: Boolean, default: false },
});

const loading = ref(false);
const loaded = ref(false);
const starting = ref(false);
const runs = ref([]);
const supported = ref(false);
const datasetRepo = ref("C-Eval");
const datasetAvailable = ref(false);
let pollTimer = null;

const isRunning = computed(() =>
  runs.value.some((run) => ["pending", "running"].includes(run.status)),
);

function formatAccuracy(value) {
  if (value === null || value === undefined) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

function statusLabel(status) {
  const labels = {
    pending: "排队中",
    running: "评测中",
    completed: "已完成",
    failed: "失败",
  };
  return labels[status] || status;
}

function statusType(status) {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "running") return "warning";
  return "info";
}

function resetPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
  if (isRunning.value) {
    pollTimer = setTimeout(loadEvaluations, 5000);
  }
}

async function loadEvaluations() {
  loading.value = !loaded.value;
  try {
    const { data } = await evaluationAPI.listQuick(
      props.repoType,
      props.namespace,
      props.name,
    );
    runs.value = data.runs || [];
    supported.value = Boolean(data.supported);
    datasetRepo.value = data.dataset_repo || datasetRepo.value;
    datasetAvailable.value = Boolean(data.dataset_available);
    loaded.value = true;
    resetPolling();
  } catch (err) {
    console.error("Failed to load evaluations:", err);
    ElMessage.error("评测记录加载失败");
  } finally {
    loading.value = false;
  }
}

async function startEvaluation() {
  starting.value = true;
  try {
    const { data } = await evaluationAPI.startQuick(
      props.repoType,
      props.namespace,
      props.name,
      { revision: props.branch },
    );
    runs.value = [data, ...runs.value.filter((run) => run.id !== data.id)];
    ElMessage.success("快速评测已开始");
    resetPolling();
  } catch (err) {
    console.error("Failed to start evaluation:", err);
    ElMessage.error(err.response?.data?.detail?.error || "快速评测启动失败");
  } finally {
    starting.value = false;
  }
}

onMounted(loadEvaluations);
onBeforeUnmount(() => {
  if (pollTimer) clearTimeout(pollTimer);
});
</script>
