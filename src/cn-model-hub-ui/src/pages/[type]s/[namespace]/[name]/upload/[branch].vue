<!-- src/cn-model-hub-ui/src/pages/[type]s/[namespace]/[name]/upload/[branch].vue -->
<template>
  <div class="container-main">
    <!-- Breadcrumb -->
    <el-breadcrumb separator="/" class="mb-6 text-gray-700 dark:text-gray-300">
      <el-breadcrumb-item>
        <RouterLink
          to="/"
          class="text-blue-600 dark:text-blue-400 hover:underline"
        >
          首页
        </RouterLink>
      </el-breadcrumb-item>
      <el-breadcrumb-item>
        <RouterLink
          :to="`/${repoType}s`"
          class="text-blue-600 dark:text-blue-400 hover:underline"
        >
          {{ repoTypeLabel }}
        </RouterLink>
      </el-breadcrumb-item>
      <el-breadcrumb-item>
        <RouterLink
          :to="`/${namespace}`"
          class="text-blue-600 dark:text-blue-400 hover:underline"
        >
          {{ namespace }}
        </RouterLink>
      </el-breadcrumb-item>
      <el-breadcrumb-item>
        <RouterLink
          :to="`/${repoType}s/${namespace}/${name}`"
          class="text-blue-600 dark:text-blue-400 hover:underline"
        >
          {{ name }}
        </RouterLink>
      </el-breadcrumb-item>
      <el-breadcrumb-item>上传文件</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- Page Header -->
    <div class="card mb-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="i-carbon-cloud-upload text-3xl text-blue-500" />
          <div>
            <h1 class="text-2xl font-bold">上传仓库文件</h1>
            <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
              将文件上传到 <strong>{{ namespace }}/{{ name }}</strong> 的
              <el-tag size="small">{{ branch }}</el-tag> 分支
            </div>
          </div>
        </div>
        <el-button @click="goBack">
          <div class="i-carbon-arrow-left inline-block mr-1" />
          返回仓库
        </el-button>
      </div>
    </div>

    <!-- Upload Form -->
    <div class="card">
      <!-- LFS Info -->
      <el-alert type="info" :closable="false" class="mb-4">
        <template #title>
          <div class="flex items-center gap-2">
            <div class="i-carbon-information" />
            大文件自动使用 LFS
          </div>
        </template>
        <div class="text-sm">
          模型权重、数据压缩包等大文件会自动走 LFS 存储。上传
          Transformers 模型时，可以直接选择整个模型目录，保留
          config.json、tokenizer 文件和 safetensors/bin 权重文件。
        </div>
      </el-alert>

      <!-- Use FileUploader Component -->
      <FileUploader
        :repo-type="repoType"
        :namespace="namespace"
        :name="name"
        :branch="branch"
        @upload-success="handleUploadSuccess"
        @upload-error="handleUploadError"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { useAuthStore } from "@/stores/auth";
import FileUploader from "@/components/repo/FileUploader.vue";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

// Route params
const repoType = computed(() => {
  const path = route.path;
  if (path.includes("/models/")) return "model";
  if (path.includes("/datasets/")) return "dataset";
  if (path.includes("/spaces/")) return "space";
  return "model";
});
const namespace = computed(() => route.params.namespace);
const name = computed(() => route.params.name);
const branch = computed(() => route.params.branch || "main");

// Computed
const repoTypeLabel = computed(() => {
  const labels = { model: "模型", dataset: "数据集", space: "空间" };
  return labels[repoType.value] || "模型";
});

// Methods
function handleUploadSuccess() {
  ElMessage.success("文件上传成功");
  // Wait a bit to show success message
  setTimeout(() => {
    router.push(`/${repoType.value}s/${namespace.value}/${name.value}`);
  }, 1000);
}

function handleUploadError(error) {
  const detail = error.response?.data?.detail;
  const errorMsg =
    (typeof detail === "string" ? detail : detail?.message || detail?.error) ||
    "文件上传失败";
  ElMessage.error(errorMsg);
  console.error("Upload error:", error);
}

function goBack() {
  router.push(`/${repoType.value}s/${namespace.value}/${name.value}`);
}

// Lifecycle
onMounted(() => {
  // Check if user has permission to upload
  if (!authStore.isAuthenticated) {
    ElMessage.error("请先登录后再上传文件");
    router.push(`/${repoType.value}s/${namespace.value}/${name.value}`);
    return;
  }

  if (!authStore.canWriteToNamespace(namespace.value)) {
    ElMessage.error("你没有权限向这个仓库上传文件");
    router.push(`/${repoType.value}s/${namespace.value}/${name.value}`);
    return;
  }
});
</script>
