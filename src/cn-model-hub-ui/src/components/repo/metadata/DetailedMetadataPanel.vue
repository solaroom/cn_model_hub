<script setup>
import { computed } from "vue";
import LicenseCard from "./LicenseCard.vue";
import LanguageCard from "./LanguageCard.vue";
import FrameworkCard from "./FrameworkCard.vue";
import MetricsCard from "./MetricsCard.vue";
import ChineseModelMetadataPanel from "./ChineseModelMetadataPanel.vue";
import { formatMetadataKey } from "@/utils/metadata-helpers";

const props = defineProps({
  metadata: {
    type: Object,
    required: true,
  },
  repoType: {
    type: String,
    required: true,
  },
});

const hasAnyContent = computed(() => {
  return Object.keys(props.metadata).length > 0;
});

const datasetConfigs = computed(() => {
  const configs = props.metadata.configs;
  if (!Array.isArray(configs)) return [];
  return configs
    .map((item) => item?.config_name || item?.name || item)
    .filter(Boolean);
});

const visibleDatasetConfigs = computed(() => datasetConfigs.value.slice(0, 12));

const datasetConfigSummary = computed(() => {
  const count = datasetConfigs.value.length;
  if (!count) return "";
  return `共 ${count} 个子集配置`;
});

// All metadata fields except the specialized ones we show as dedicated cards
const specializedFields = new Set([
  "license",
  "license_name",
  "license_link",
  "language",
  "library_name",
  "pipeline_tag",
  "base_model",
  "datasets",
  "task_categories",
  "size_categories",
  "multilinguality",
  "annotations_creators",
  "source_datasets",
  "eval_results",
  "eval_results_chinese",
  "cn_model",
  "pretty_name",
  "configs",
  "data_files",
  "features",
  "splits",
  "dataset_info",
  "builder_name",
  "config_name",
]);

const otherFields = computed(() => {
  const others = [];
  for (const [key, value] of Object.entries(props.metadata)) {
    if (!specializedFields.has(key) && shouldShowOtherField(key, value)) {
      others.push({ key, value });
    }
  }
  return others.sort((a, b) => a.key.localeCompare(b.key));
});

function shouldShowOtherField(key, value) {
  if (props.repoType !== "dataset") return true;
  if (Array.isArray(value) && value.length > 12) return false;
  if (typeof value === "object" && value !== null) return false;
  return !String(key).toLowerCase().includes("file");
}

function displayScalar(value) {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}
</script>

<template>
  <div
    v-if="hasAnyContent"
    class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
  >
    <LicenseCard v-if="metadata.license" :metadata="metadata" />

    <LanguageCard v-if="metadata.language" :languages="metadata.language" />

    <FrameworkCard
      v-if="
        repoType === 'model' && (metadata.library_name || metadata.pipeline_tag)
      "
      :metadata="metadata"
    />

    <ChineseModelMetadataPanel
      v-if="repoType === 'model' && (metadata.cn_model || metadata.eval_results_chinese)"
      :metadata="metadata"
    />

    <div v-if="repoType === 'model' && metadata.base_model" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        基座模型
      </h3>
      <div class="space-y-1">
        <RouterLink
          v-for="model in Array.isArray(metadata.base_model)
            ? metadata.base_model
            : [metadata.base_model]"
          :key="model"
          :to="`/models/${model}`"
          class="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors group"
        >
          <div
            class="i-carbon-model text-base text-blue-500 dark:text-blue-400 flex-shrink-0"
          />
          <span
            class="text-sm text-blue-600 dark:text-blue-400 group-hover:underline truncate"
          >
            {{ model }}
          </span>
        </RouterLink>
      </div>
    </div>

    <div v-if="repoType === 'model' && metadata.datasets" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        训练数据集
      </h3>
      <div class="space-y-1">
        <RouterLink
          v-for="dataset in Array.isArray(metadata.datasets)
            ? metadata.datasets
            : [metadata.datasets]"
          :key="dataset"
          :to="`/datasets/${dataset}`"
          class="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors group"
        >
          <div
            class="i-carbon-data-set text-base text-green-500 dark:text-green-400 flex-shrink-0"
          />
          <span
            class="text-sm text-blue-600 dark:text-blue-400 group-hover:underline truncate"
          >
            {{ dataset }}
          </span>
        </RouterLink>
      </div>
    </div>

    <div v-if="repoType === 'dataset' && metadata.task_categories" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        任务
      </h3>
      <div class="flex flex-wrap gap-2">
        <el-tag
          v-for="task in Array.isArray(metadata.task_categories)
            ? metadata.task_categories
            : [metadata.task_categories]"
          :key="task"
          size="small"
          type="success"
        >
          {{ task }}
        </el-tag>
      </div>
    </div>

    <div v-if="repoType === 'dataset' && metadata.size_categories" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">数据规模</h3>
      <el-tag size="large" type="info">
        {{
          Array.isArray(metadata.size_categories)
            ? metadata.size_categories[0]
            : metadata.size_categories
        }}
      </el-tag>
    </div>

    <div v-if="repoType === 'dataset' && metadata.multilinguality" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        语言类型
      </h3>
      <div class="text-sm text-gray-900 dark:text-white">
        {{ metadata.multilinguality }}
      </div>
    </div>

    <div
      v-if="repoType === 'dataset' && metadata.annotations_creators"
      class="card"
    >
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        标注来源
      </h3>
      <div class="flex flex-wrap gap-2">
        <el-tag
          v-for="creator in Array.isArray(metadata.annotations_creators)
            ? metadata.annotations_creators
            : [metadata.annotations_creators]"
          :key="creator"
          size="small"
        >
          {{ creator }}
        </el-tag>
      </div>
    </div>

    <div v-if="repoType === 'dataset' && metadata.source_datasets" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">来源数据集</h3>
      <div class="flex flex-wrap gap-2">
        <el-tag
          v-for="source in Array.isArray(metadata.source_datasets)
            ? metadata.source_datasets
            : [metadata.source_datasets]"
          :key="source"
          size="small"
          type="warning"
        >
          {{ source }}
        </el-tag>
      </div>
    </div>

    <div v-if="repoType === 'dataset' && datasetConfigs.length" class="card md:col-span-2 lg:col-span-3">
      <div class="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h3 class="font-semibold text-gray-900 dark:text-white">子集配置</h3>
        <span class="text-xs text-gray-500 dark:text-gray-400">
          {{ datasetConfigSummary }}，仅展示前 {{ visibleDatasetConfigs.length }} 个
        </span>
      </div>
      <div class="flex flex-wrap gap-2">
        <el-tag
          v-for="config in visibleDatasetConfigs"
          :key="config"
          size="small"
          type="info"
        >
          {{ config }}
        </el-tag>
      </div>
    </div>

    <MetricsCard
      v-if="repoType === 'model' && metadata.eval_results"
      :results="metadata.eval_results"
    />

    <div v-for="field in otherFields" :key="field.key" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        {{ formatMetadataKey(field.key) }}
      </h3>
      <div class="text-sm">
        <!-- String value -->
        <div
          v-if="typeof field.value === 'string'"
          class="text-gray-900 dark:text-white"
        >
          {{ displayScalar(field.value) }}
        </div>
        <!-- Number or boolean -->
        <div
          v-else-if="
            typeof field.value === 'number' || typeof field.value === 'boolean'
          "
          class="text-gray-900 dark:text-white"
        >
          {{ displayScalar(field.value) }}
        </div>
        <!-- Array -->
        <div
          v-else-if="Array.isArray(field.value)"
          class="flex flex-wrap gap-2"
        >
          <el-tag v-for="(item, idx) in field.value" :key="idx" size="small">
            {{ item }}
          </el-tag>
        </div>
        <!-- Object -->
        <pre
          v-else
          class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto"
        ><code class="text-gray-900 dark:text-gray-100">{{ JSON.stringify(field.value, null, 2) }}</code></pre>
      </div>
    </div>
  </div>
</template>
