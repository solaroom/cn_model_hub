<script setup>
const props = defineProps({
  metadata: {
    type: Object,
    required: true,
  },
});

const cn = computed(() => props.metadata.cn_model || {});

const hasChineseMetadata = computed(() => {
  return Object.keys(cn.value).length > 0 || hasChineseEval.value;
});

const basicRows = computed(() =>
  [
    ["中文名称", cn.value.display_name],
    ["模型系列", cn.value.model_family],
    ["模型类型", cn.value.model_type],
    ["参数量", cn.value.parameter_count],
    ["上下文长度", cn.value.context_length],
    ["发布机构", cn.value.organization],
    ["发布日期", cn.value.release_date],
    ["基座模型", cn.value.base_model || props.metadata.base_model],
  ].filter((row) => row[1] !== undefined && row[1] !== null && row[1] !== ""),
);

const runtimeRows = computed(() =>
  [
    ["推理框架", cn.value.inference_frameworks],
    ["量化格式", cn.value.quantization],
    ["输入模态", cn.value.input_modalities],
    ["输出模态", cn.value.output_modalities],
    ["商用限制", cn.value.commercial_use],
    ["联系方式", cn.value.contact],
  ].filter((row) => row[1] !== undefined && row[1] !== null && row[1] !== ""),
);

const capabilityGroups = computed(() =>
  [
    ["任务", cn.value.tasks],
    ["中文能力", cn.value.chinese_capabilities],
    ["适用领域", cn.value.domains],
    ["推荐用途", cn.value.recommended_use],
    ["使用限制", cn.value.limitations],
  ].filter((group) => toList(group[1]).length > 0),
);

const chineseEvalResults = computed(() => {
  const results = props.metadata.eval_results_chinese || cn.value.eval_results || [];
  return Array.isArray(results) ? results : [results];
});

const hasChineseEval = computed(() => chineseEvalResults.value.length > 0);

function toList(value) {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function formatValue(value) {
  const values = toList(value);
  if (values.length > 1) return values.join("、");
  return values[0];
}
</script>

<template>
  <template v-if="hasChineseMetadata">
    <div v-if="basicRows.length" class="card">
      <h3 class="mb-3 font-semibold text-gray-900 dark:text-white">
        中文模型信息
      </h3>
      <div class="space-y-2 text-sm">
        <div
          v-for="[label, value] in basicRows"
          :key="label"
          class="flex items-start justify-between gap-3"
        >
          <span class="shrink-0 text-gray-500 dark:text-gray-400">
            {{ label }}
          </span>
          <span class="min-w-0 text-right font-medium text-gray-900 dark:text-white">
            {{ formatValue(value) }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="capabilityGroups.length" class="card md:col-span-2">
      <h3 class="mb-3 font-semibold text-gray-900 dark:text-white">
        中文能力与用途
      </h3>
      <div class="space-y-4">
        <div v-for="[label, values] in capabilityGroups" :key="label">
          <div class="mb-2 text-sm text-gray-500 dark:text-gray-400">
            {{ label }}
          </div>
          <div class="flex flex-wrap gap-2">
            <el-tag
              v-for="item in toList(values)"
              :key="item"
              size="small"
              effect="plain"
            >
              {{ item }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <div v-if="runtimeRows.length" class="card">
      <h3 class="mb-3 font-semibold text-gray-900 dark:text-white">
        推理与发布
      </h3>
      <div class="space-y-2 text-sm">
        <div
          v-for="[label, value] in runtimeRows"
          :key="label"
          class="flex items-start justify-between gap-3"
        >
          <span class="shrink-0 text-gray-500 dark:text-gray-400">
            {{ label }}
          </span>
          <span class="min-w-0 text-right font-medium text-gray-900 dark:text-white">
            {{ formatValue(value) }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="hasChineseEval" class="card md:col-span-2 lg:col-span-3">
      <h3 class="mb-3 font-semibold text-gray-900 dark:text-white">
        中文评测结果
      </h3>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-gray-200 text-gray-500 dark:border-gray-700 dark:text-gray-400">
            <tr>
              <th class="py-2 pr-4 font-medium">榜单</th>
              <th class="py-2 pr-4 font-medium">数据集</th>
              <th class="py-2 pr-4 font-medium">指标</th>
              <th class="py-2 pr-4 font-medium">分数</th>
              <th class="py-2 pr-4 font-medium">划分</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in chineseEvalResults"
              :key="idx"
              class="border-b border-gray-100 last:border-0 dark:border-gray-800"
            >
              <td class="py-2 pr-4 font-medium text-gray-900 dark:text-white">
                {{ row.benchmark || row.task || "-" }}
              </td>
              <td class="py-2 pr-4">{{ row.dataset || row.config || "-" }}</td>
              <td class="py-2 pr-4">{{ row.metric || "-" }}</td>
              <td class="py-2 pr-4">{{ row.score ?? row.value ?? "-" }}</td>
              <td class="py-2 pr-4">{{ row.split || "-" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </template>
</template>
