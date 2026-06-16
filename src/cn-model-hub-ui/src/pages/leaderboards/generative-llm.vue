<template>
  <div class="container-main">
    <div class="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <h1 class="text-3xl font-bold">生成式大语言模型排行榜</h1>
        <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
          {{ leaderboard?.metric_label || "C-Eval 20题准确率" }}
        </p>
      </div>
      <el-button @click="loadLeaderboard">
        <div class="i-carbon-renew mr-1 inline-block" />
        刷新
      </el-button>
    </div>

    <div class="card">
      <div v-if="loading" class="py-16 text-center text-gray-500 dark:text-gray-400">
        <el-icon class="is-loading" :size="36">
          <div class="i-carbon-loading" />
        </el-icon>
      </div>
      <div v-else-if="entries.length === 0" class="py-16 text-center text-gray-500 dark:text-gray-400">
        暂无完成评测的模型
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="border-b border-gray-200 text-left text-gray-500 dark:border-gray-700 dark:text-gray-400">
            <tr>
              <th class="py-3 pr-4 font-medium">排名</th>
              <th class="py-3 pr-4 font-medium">模型</th>
              <th class="py-3 pr-4 font-medium">类型</th>
              <th class="py-3 pr-4 font-medium">正确数</th>
              <th class="py-3 pr-4 font-medium">准确率</th>
              <th class="py-3 pr-4 font-medium">数据集</th>
              <th class="py-3 pr-4 font-medium">提交</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="entry in entries"
              :key="entry.id"
              class="border-b border-gray-100 dark:border-gray-800"
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
              <td class="py-3 pr-4">{{ displayDatasetRepo(entry.dataset_repo) }}</td>
              <td class="py-3 pr-4 font-mono text-xs">
                {{ entry.commit_id ? entry.commit_id.slice(0, 7) : "-" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p v-if="leaderboard?.ranking_rule" class="mt-4 text-sm text-gray-500 dark:text-gray-400">
      {{ leaderboard.ranking_rule }}
    </p>
  </div>
</template>

<script setup>
import { ElMessage } from "element-plus";
import { evaluationAPI } from "@/utils/api";

const loading = ref(false);
const leaderboard = ref(null);
const entries = ref([]);

function formatAccuracy(value) {
  if (value === null || value === undefined) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

function displayDatasetRepo(value) {
  if (!value) return "-";
  return String(value).split("/").pop();
}

async function loadLeaderboard() {
  loading.value = true;
  try {
    const { data } = await evaluationAPI.leaderboard("generative-llm");
    leaderboard.value = data;
    entries.value = data.entries || [];
  } catch (err) {
    console.error("Failed to load leaderboard:", err);
    ElMessage.error("排行榜加载失败");
  } finally {
    loading.value = false;
  }
}

onMounted(loadLeaderboard);
</script>
