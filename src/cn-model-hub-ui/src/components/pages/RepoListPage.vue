<!-- src/cn-model-hub-ui/src/components/pages/RepoListPage.vue -->
<template>
  <div class="container-main">
    <div
      class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6"
    >
      <div>
        <h1 class="text-2xl md:text-3xl font-bold mb-2">{{ pageTitle }}</h1>
        <p class="text-sm md:text-base text-gray-600 dark:text-gray-400">
          {{ pageDescription }}
        </p>
      </div>

      <el-button
        v-if="isAuthenticated"
        type="primary"
        size="large"
        @click="showCreateDialog = true"
        class="w-full md:w-auto"
      >
        <div class="i-carbon-add inline-block mr-1" />
        新建{{ repoTypeLabel }}
      </el-button>
    </div>

    <!-- Filters -->
    <div class="card mb-6">
      <div
        class="flex flex-col gap-4 md:flex-row md:items-center"
      >
        <div class="w-full md:flex-1 md:min-w-0">
          <el-input
            v-model="searchQuery"
            :placeholder="`搜索${pageTitle}...`"
            clearable
            class="w-full"
          >
            <template #prefix>
              <div class="i-carbon-search" />
            </template>
          </el-input>
        </div>

        <div class="w-full md:w-72 md:flex-none md:shrink-0">
          <el-select
            v-model="sortBy"
            placeholder="排序方式"
            class="w-full"
          >
            <el-option label="最近创建" value="recent" />
            <el-option label="最近更新" value="updated" />
            <el-option label="下载最多" value="downloads" />
            <el-option label="点赞最多" value="likes" />
          </el-select>
        </div>
      </div>

      <div
        v-if="searchPresets.length"
        class="mt-4 flex flex-wrap gap-2"
      >
        <el-button
          v-for="preset in searchPresets"
          :key="preset.value"
          size="small"
          round
          :type="searchQuery === preset.value ? 'primary' : 'default'"
          @click="applySearchPreset(preset.value)"
        >
          {{ preset.label }}
        </el-button>
      </div>
    </div>

    <!-- Repository List -->
    <el-skeleton :loading="loading" :rows="5" animated>
      <RepoList :repos="repos" :type="repoType" />
    </el-skeleton>

    <!-- Create Repository Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      :title="`新建${repoTypeLabel}`"
      width="500px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item :label="`${repoTypeLabel}名称`" prop="name">
          <el-input v-model="form.name" :placeholder="`my-${repoType}`" />
          <div class="text-xs text-gray-500 mt-1">
            完整名称：{{ currentUser }}/{{ form.name || `${repoType}-name` }}
          </div>
        </el-form-item>

        <el-form-item label="组织（可选）" prop="organization">
          <el-select
            v-model="form.organization"
            placeholder="选择组织或留空"
            clearable
            class="w-full"
          >
            <el-option
              v-for="org in userOrgs"
              :key="org.name"
              :label="org.name"
              :value="org.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.private">
            将此{{ repoTypeLabel }}设为私有
          </el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">
          创建{{ repoTypeLabel }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { repoAPI, orgAPI, searchAPI } from "@/utils/api";
import { useAuthStore } from "@/stores/auth";
import RepoList from "@/components/repo/RepoList.vue";
import {
  getRepoSortPreference,
  setRepoSortPreference,
} from "@/utils/repoSortPreference";
import { ElMessage } from "element-plus";

const props = defineProps({
  repoType: {
    type: String,
    required: true,
    validator: (value) => ["model", "dataset", "space"].includes(value),
  },
});

const router = useRouter();
const authStore = useAuthStore();
const { isAuthenticated, username: currentUser } = storeToRefs(authStore);

const repoTypeLabel = computed(() => {
  const labels = { model: "模型", dataset: "数据集", space: "空间" };
  return labels[props.repoType] || "模型";
});

const pageTitle = computed(() => {
  const titles = { model: "模型", dataset: "数据集", space: "空间" };
  return titles[props.repoType] || "模型";
});

const pageDescription = computed(() => {
  const descriptions = {
    model: "浏览并共享中文开源 AI 模型",
    dataset: "浏览并共享机器学习数据集",
    space: "浏览模型演示与应用空间",
  };
  return descriptions[props.repoType] || "";
});

const modelSearchPresets = [
  { label: "千问", value: "千问" },
  { label: "DeepSeek", value: "deepseek" },
  { label: "中文对话", value: "中文 对话" },
  { label: "嵌入模型", value: "嵌入 模型" },
  { label: "多模态", value: "多模态" },
];

const searchPresets = computed(() =>
  props.repoType === "model" ? modelSearchPresets : [],
);

const loading = ref(true);
const repos = ref([]);
const searchQuery = ref("");
const sortBy = ref(
  getRepoSortPreference({
    scope: "repo",
    repoType: props.repoType,
    allowedValues: ["recent", "updated", "downloads", "likes"],
    fallback: "recent",
  }),
);
const showCreateDialog = ref(false);
const creating = ref(false);
const userOrgs = ref([]);
const formRef = ref(null);

const form = reactive({
  name: "",
  organization: "",
  private: false,
});

let searchDebounceHandle = null;
let skipNextSearchWatcher = false;
let repositoryRequestId = 0;

const rules = {
  name: [
    {
      required: true,
      message: `请输入${repoTypeLabel.value}名称`,
      trigger: "blur",
    },
    {
      pattern: /^[a-zA-Z0-9_-]+$/,
      message: "仅允许字母、数字、连字符和下划线",
      trigger: "blur",
    },
  ],
};

function currentSearchTerm() {
  return searchQuery.value.trim();
}

function applySearchPreset(value) {
  if (searchQuery.value !== value) {
    skipNextSearchWatcher = true;
    searchQuery.value = value;
  }
  if (searchDebounceHandle) {
    clearTimeout(searchDebounceHandle);
    searchDebounceHandle = null;
  }
  loadRepositoryResults();
}

async function loadRepos(requestId) {
  loading.value = true;
  try {
    const { data } = await repoAPI.listRepos(props.repoType, {
      limit: 100,
      sort: sortBy.value,
      fallback: false, // Don't aggregate external repos on main list pages
    });
    if (requestId !== repositoryRequestId) return;
    repos.value = data;
  } catch (err) {
    console.error(`Failed to load ${props.repoType}s:`, err);
    ElMessage.error(`加载${pageTitle.value}失败`);
  } finally {
    if (requestId === repositoryRequestId) {
      loading.value = false;
    }
  }
}

async function searchRepos(requestId) {
  loading.value = true;
  try {
    const { data } = await searchAPI.search({
      q: currentSearchTerm(),
      repo_type: props.repoType,
      sort: sortBy.value === "updated" ? "recent" : sortBy.value,
      limit: 100,
      include_users: false,
    });
    if (requestId !== repositoryRequestId) return;
    repos.value = data.repositories || [];
  } catch (err) {
    console.error(`Failed to search ${props.repoType}s:`, err);
    ElMessage.error(`搜索${pageTitle.value}失败`);
  } finally {
    if (requestId === repositoryRequestId) {
      loading.value = false;
    }
  }
}

function loadRepositoryResults() {
  const requestId = repositoryRequestId + 1;
  repositoryRequestId = requestId;
  if (currentSearchTerm()) {
    return searchRepos(requestId);
  }
  return loadRepos(requestId);
}

async function loadUserOrgs() {
  if (!currentUser.value) return;

  try {
    const { data } = await orgAPI.getUserOrgs(currentUser.value);
    userOrgs.value = data.organizations || [];
  } catch (err) {
    console.error("Failed to load organizations:", err);
  }
}

async function handleCreate() {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (!valid) return;

    creating.value = true;
    try {
      const { data } = await repoAPI.create({
        type: props.repoType,
        name: form.name,
        organization: form.organization || null,
        private: form.private,
      });

      ElMessage.success(`${repoTypeLabel.value}创建成功`);
      showCreateDialog.value = false;

      const repoId =
        data.repo_id ||
        `${form.organization || currentUser.value}/${form.name}`;
      router.push(`/${props.repoType}s/${repoId}`);
    } catch (err) {
      // `POST /api/repos/create` returns a 409 with a top-level `{url,
      // repo_id, error}` body when the repo already exists (HF-compatible
      // exist-ok contract). Read `.error` before falling back to the
      // legacy `.detail` shape so the user sees the actual conflict
      // message instead of a generic "Failed to create ..." toast.
      ElMessage.error(
        err.response?.data?.error ||
          err.response?.data?.detail ||
          `创建${repoTypeLabel.value}失败`,
      );
    } finally {
      creating.value = false;
    }
  });
}

watch(showCreateDialog, (val) => {
  if (val) {
    loadUserOrgs();
  } else {
    form.name = "";
    form.organization = "";
    form.private = false;
  }
});

// Reload repos when sort changes
watch(sortBy, () => {
  setRepoSortPreference({
    scope: "repo",
    repoType: props.repoType,
    value: sortBy.value,
  });
  loadRepositoryResults();
});

watch(searchQuery, () => {
  if (skipNextSearchWatcher) {
    skipNextSearchWatcher = false;
    return;
  }
  if (searchDebounceHandle) {
    clearTimeout(searchDebounceHandle);
  }
  searchDebounceHandle = setTimeout(() => {
    searchDebounceHandle = null;
    loadRepositoryResults();
  }, 300);
});

onMounted(() => {
  loadRepositoryResults();
});
</script>
