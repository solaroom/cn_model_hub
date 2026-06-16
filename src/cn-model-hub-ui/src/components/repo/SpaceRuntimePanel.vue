<template>
  <div class="space-y-4">
    <div class="card">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 class="text-xl font-semibold">{{ runtimeTitle }}</h2>
          <div class="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <el-tag :type="statusTagType" effect="plain">
              {{ statusLabel }}
            </el-tag>
            <span v-if="runtime.commit_id" class="font-mono text-xs">
              {{ runtime.commit_id.slice(0, 7) }}
            </span>
            <span v-if="mlflow.enabled">
              MLflow: {{ mlflow.status }}
            </span>
          </div>
        </div>

        <div class="flex flex-col gap-2 sm:flex-row">
          <el-button
            v-if="isOwner"
            type="primary"
            :loading="starting"
            @click="startRuntime"
          >
            <div class="i-carbon-play mr-1 inline-block" />
            {{ runtime.status === "running" ? "重启" : "启动" }}
          </el-button>
          <el-button
            v-if="isOwner && runtime.status === 'running'"
            :loading="stopping"
            plain
            @click="stopRuntime"
          >
            <div class="i-carbon-stop mr-1 inline-block" />
            停止
          </el-button>
          <el-button :loading="loading" plain @click="refresh">
            <div class="i-carbon-renew mr-1 inline-block" />
            刷新
          </el-button>
        </div>
      </div>

      <p
        v-if="runtime.message"
        class="mt-4 rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-600 dark:bg-gray-900 dark:text-gray-300"
      >
        {{ runtime.message }}
      </p>
    </div>

    <div v-if="runtime.status === 'running' && runtime.proxy_url" class="overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      <iframe
        :key="runtime.proxy_url"
        :src="runtime.proxy_url"
        :title="runtimeTitle"
        class="h-[720px] w-full border-0"
        allow="clipboard-read; clipboard-write"
      />
    </div>

    <div
      v-else
      class="card py-14 text-center text-gray-500 dark:text-gray-400"
    >
      <div class="i-carbon-application-web mb-4 inline-block text-6xl" />
      <p v-if="isOwner">{{ ownerEmptyText }}</p>
      <p v-else>{{ visitorEmptyText }}</p>
    </div>

    <div v-if="runtime.logs?.length" class="card">
      <div class="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex flex-wrap items-center gap-2">
          <h3 class="font-semibold">运行日志</h3>
          <el-tag size="small" effect="plain">{{ runtime.logs.length }} 行</el-tag>
          <el-tag v-if="runtime.log_limit" size="small" effect="plain">
            最多保留 {{ runtime.log_limit }} 行
          </el-tag>
        </div>
        <div class="flex items-center gap-2">
          <el-button size="small" plain @click="copyLogs">
            <div class="i-carbon-copy mr-1 inline-block" />
            复制
          </el-button>
          <el-button size="small" plain @click="refresh">
            <div class="i-carbon-renew mr-1 inline-block" />
            刷新日志
          </el-button>
        </div>
      </div>
      <pre
        ref="logRef"
        class="max-h-[70vh] min-h-[24rem] overflow-auto whitespace-pre-wrap break-words rounded bg-gray-950 p-4 font-mono text-xs leading-5 text-gray-100"
      >{{ logText }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ElMessage } from "element-plus";
import { mlflowAPI, runtimeAPI } from "@/utils/api";

const props = defineProps({
  repoType: { type: String, default: "space" },
  namespace: { type: String, required: true },
  name: { type: String, required: true },
  branch: { type: String, default: "main" },
  isOwner: { type: Boolean, default: false },
});

const loading = ref(false);
const starting = ref(false);
const stopping = ref(false);
const logRef = ref(null);
let refreshTimer = null;
const runtime = ref({
  status: "stopped",
  message: "",
  proxy_url: "",
  logs: [],
});
const mlflow = ref({
  enabled: false,
  status: "disabled",
});

const statusLabel = computed(() => {
  const labels = {
    running: "运行中",
    starting: "启动中",
    stopped: "未启动",
    error: "启动失败",
  };
  return labels[runtime.value.status] || runtime.value.status;
});

const statusTagType = computed(() => {
  if (runtime.value.status === "running") return "success";
  if (runtime.value.status === "error") return "danger";
  if (runtime.value.status === "starting") return "warning";
  return "info";
});

const runtimeTitle = computed(() =>
  props.repoType === "model" ? "本地模型运行" : "Space 运行",
);

const ownerEmptyText = computed(() =>
  props.repoType === "model"
    ? "点击启动后会加载当前模型仓库中的本地权重；如仓库没有 app.py，将使用内置 Qwen2.5-0.5B 模板。"
    : "点击启动后会运行仓库根目录的 app.py。",
);

const visitorEmptyText = computed(() =>
  props.repoType === "model"
    ? "模型 demo 还没有启动，请仓库维护者先启动本地推理。"
    : "Space 还没有启动，请仓库维护者先启动应用。",
);

const logText = computed(() => (runtime.value.logs || []).join("\n"));

const shouldPollRuntime = computed(() =>
  ["starting", "running"].includes(runtime.value.status),
);

async function copyLogs() {
  try {
    await navigator.clipboard.writeText(logText.value);
    ElMessage.success("日志已复制");
  } catch (err) {
    console.error("Failed to copy runtime logs:", err);
    ElMessage.error("复制日志失败");
  }
}

function scrollLogsToBottom() {
  nextTick(() => {
    if (!logRef.value) return;
    logRef.value.scrollTop = logRef.value.scrollHeight;
  });
}

function updatePolling() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  if (shouldPollRuntime.value) {
    refreshTimer = setInterval(refresh, 3000);
  }
}

async function refresh() {
  loading.value = true;
  try {
    const [{ data: runtimeData }, { data: mlflowData }] = await Promise.all([
      runtimeAPI.status(props.repoType, props.namespace, props.name),
      mlflowAPI.status(),
    ]);
    runtime.value = runtimeData;
    mlflow.value = mlflowData;
    scrollLogsToBottom();
  } catch (err) {
    console.error("Failed to load runtime status:", err);
    ElMessage.error(err.response?.data?.detail?.error || "加载运行状态失败");
  } finally {
    loading.value = false;
    updatePolling();
  }
}

async function startRuntime() {
  starting.value = true;
  runtime.value = {
    ...runtime.value,
    status: "starting",
    message: "启动请求已发送，模型和依赖可能需要较长时间加载。",
  };
  updatePolling();
  try {
    const { data } = await runtimeAPI.start(
      props.repoType,
      props.namespace,
      props.name,
      {
        revision: props.branch,
      },
    );
    runtime.value = data;
    scrollLogsToBottom();
    if (data.status === "running") {
      ElMessage.success("运行时已启动");
    } else if (data.status === "starting") {
      ElMessage.info("运行时正在启动");
    } else if (data.status === "error") {
      ElMessage.error("运行时启动失败，请查看日志");
    }
  } catch (err) {
    console.error("Failed to start runtime:", err);
    if (err.code === "ECONNABORTED") {
      runtime.value = {
        ...runtime.value,
        status: "starting",
        message: "启动仍在进行中，请继续查看运行日志。",
      };
      ElMessage.info("启动耗时较长，正在继续刷新状态");
    } else {
      ElMessage.error(err.response?.data?.detail?.error || "启动运行时失败");
    }
    await refresh();
  } finally {
    starting.value = false;
    updatePolling();
  }
}

async function stopRuntime() {
  stopping.value = true;
  try {
    const { data } = await runtimeAPI.stop(
      props.repoType,
      props.namespace,
      props.name,
    );
    runtime.value = data;
    ElMessage.success("运行时已停止");
    scrollLogsToBottom();
  } catch (err) {
    console.error("Failed to stop runtime:", err);
    ElMessage.error(err.response?.data?.detail?.error || "停止运行时失败");
  } finally {
    stopping.value = false;
    updatePolling();
  }
}

onMounted(refresh);
onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>
