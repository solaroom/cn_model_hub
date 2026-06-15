<template>
  <div class="card">
    <div class="mb-3 flex items-start justify-between gap-3">
      <div>
        <h3 class="font-semibold">MLflow</h3>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
          {{ statusText }}
        </p>
      </div>
      <el-tag :type="tagType" effect="plain">
        {{ tagLabel }}
      </el-tag>
    </div>

    <div v-if="binding.experiment_name" class="space-y-2 text-sm">
      <div>
        <span class="text-gray-600 dark:text-gray-400">Experiment:</span>
        <div class="mt-1 break-all font-mono text-xs">
          {{ binding.experiment_name }}
        </div>
      </div>
      <div v-if="binding.experiment_id">
        <span class="text-gray-600 dark:text-gray-400">ID:</span>
        <span class="ml-2 font-mono text-xs">{{ binding.experiment_id }}</span>
      </div>
      <div v-if="binding.last_synced_at">
        <span class="text-gray-600 dark:text-gray-400">Last synced:</span>
        <span class="ml-2">{{ formatDate(binding.last_synced_at) }}</span>
      </div>
    </div>

    <div v-if="errorMessage" class="mt-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300">
      {{ errorMessage }}
    </div>

    <div class="mt-4 flex flex-wrap gap-2">
      <el-button
        v-if="isOwner && !binding.enabled"
        type="primary"
        size="small"
        :loading="bindingActionLoading"
        @click="bindRepository"
      >
        Bind Experiment
      </el-button>
      <el-button
        v-if="isOwner && binding.enabled"
        size="small"
        plain
        :loading="bindingActionLoading"
        @click="unbindRepository"
      >
        Unbind
      </el-button>
      <el-button
        size="small"
        plain
        :loading="loading"
        @click="refresh"
      >
        Refresh
      </el-button>
    </div>

    <div v-if="binding.enabled" class="mt-5">
      <div class="mb-2 flex items-center justify-between">
        <h4 class="font-medium">Recent Runs</h4>
        <span class="text-xs text-gray-500 dark:text-gray-400">
          {{ runs.length }}
        </span>
      </div>

      <div v-if="runsLoading" class="py-6 text-sm text-gray-500 dark:text-gray-400">
        Loading runs...
      </div>
      <div
        v-else-if="runs.length === 0"
        class="rounded border border-dashed border-gray-200 px-3 py-4 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400"
      >
        No runs yet.
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="run in runs"
          :key="run.run_id"
          class="rounded border border-gray-200 px-3 py-3 dark:border-gray-700"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="truncate font-medium">
                {{ run.run_name || run.run_id }}
              </div>
              <div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {{ run.status || "UNKNOWN" }}
              </div>
            </div>
            <div class="text-right text-xs text-gray-500 dark:text-gray-400">
              {{ formatEpoch(run.start_time) }}
            </div>
          </div>
          <div
            v-if="metricEntries(run).length"
            class="mt-2 flex flex-wrap gap-2 text-xs"
          >
            <span
              v-for="item in metricEntries(run)"
              :key="item.key"
              class="rounded bg-gray-100 px-2 py-1 dark:bg-gray-800"
            >
              {{ item.key }}: {{ item.value }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ElMessage } from "element-plus";
import { mlflowAPI } from "@/utils/api";
import { formatRelativeTime } from "@/utils/datetime";

const emit = defineEmits(["binding-updated"]);

const props = defineProps({
  repoType: { type: String, required: true },
  namespace: { type: String, required: true },
  name: { type: String, required: true },
  isOwner: { type: Boolean, default: false },
  initialBinding: {
    type: Object,
    default: () => ({
      enabled: false,
      experiment_name: null,
      experiment_id: null,
      last_synced_at: null,
    }),
  },
});

const loading = ref(false);
const runsLoading = ref(false);
const bindingActionLoading = ref(false);
const errorMessage = ref("");
const binding = ref({
  enabled: false,
  experiment_name: null,
  experiment_id: null,
  last_synced_at: null,
  ...(props.initialBinding || {}),
});
const runs = ref([]);

const tagType = computed(() => (binding.value.enabled ? "success" : "info"));
const tagLabel = computed(() => (binding.value.enabled ? "Bound" : "Unbound"));
const statusText = computed(() =>
  binding.value.enabled
    ? "This repository is connected to an MLflow experiment."
    : "This repository is not bound to an MLflow experiment yet.",
);

function formatDate(value) {
  return formatRelativeTime(value, "unknown");
}

function formatEpoch(value) {
  if (!value) return "unknown";
  return formatRelativeTime(new Date(Number(value)).toISOString(), "unknown");
}

function metricEntries(run) {
  return Object.entries(run.metrics || {})
    .slice(0, 4)
    .map(([key, value]) => ({ key, value }));
}

async function loadBinding() {
  const { data } = await mlflowAPI.getBinding(
    props.repoType,
    props.namespace,
    props.name,
  );
  binding.value = data;
  emit("binding-updated", data);
}

async function loadRuns() {
  if (!binding.value.enabled) {
    runs.value = [];
    return;
  }
  runsLoading.value = true;
  try {
    const { data } = await mlflowAPI.listRuns(
      props.repoType,
      props.namespace,
      props.name,
      { limit: 10 },
    );
    runs.value = data.runs || [];
  } finally {
    runsLoading.value = false;
  }
}

async function refresh() {
  loading.value = true;
  errorMessage.value = "";
  try {
    await loadBinding();
    await loadRuns();
  } catch (err) {
    console.error("Failed to load MLflow binding:", err);
    errorMessage.value =
      err.response?.data?.detail || "Failed to load MLflow state";
  } finally {
    loading.value = false;
  }
}

async function bindRepository() {
  bindingActionLoading.value = true;
  errorMessage.value = "";
  try {
    await mlflowAPI.bind(props.repoType, props.namespace, props.name);
    ElMessage.success("MLflow experiment bound");
    await refresh();
  } catch (err) {
    console.error("Failed to bind MLflow experiment:", err);
    errorMessage.value =
      err.response?.data?.detail || "Failed to bind MLflow experiment";
    ElMessage.error(errorMessage.value);
  } finally {
    bindingActionLoading.value = false;
  }
}

async function unbindRepository() {
  bindingActionLoading.value = true;
  errorMessage.value = "";
  try {
    await mlflowAPI.unbind(props.repoType, props.namespace, props.name);
    ElMessage.success("MLflow experiment unbound");
    await refresh();
  } catch (err) {
    console.error("Failed to unbind MLflow experiment:", err);
    errorMessage.value =
      err.response?.data?.detail || "Failed to unbind MLflow experiment";
    ElMessage.error(errorMessage.value);
  } finally {
    bindingActionLoading.value = false;
  }
}

watch(
  () => props.initialBinding,
  (nextValue) => {
    binding.value = {
      enabled: false,
      experiment_name: null,
      experiment_id: null,
      last_synced_at: null,
      ...(nextValue || {}),
    };
  },
  { deep: true },
);

onMounted(async () => {
  await refresh();
});
</script>
