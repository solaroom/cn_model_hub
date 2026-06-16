<template>
  <div class="container-main">
    <div class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <h1 class="mb-2 text-2xl font-bold md:text-3xl">空间</h1>
        <p class="text-sm text-gray-600 dark:text-gray-400 md:text-base">
          已创建 Demo
        </p>
      </div>
      <el-button size="large" @click="loadDemos">
        <div class="i-carbon-renew mr-1 inline-block" />
        刷新
      </el-button>
    </div>

    <el-skeleton :loading="loading" :rows="5" animated>
      <div v-if="demos.length === 0" class="card py-14 text-center text-gray-500 dark:text-gray-400">
        暂无已创建 Demo
      </div>

      <div v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <article
          v-for="demo in demos"
          :key="demo.id"
          class="card flex min-h-48 flex-col justify-between"
        >
          <div>
            <div class="mb-3 flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="mb-2 flex flex-wrap items-center gap-2">
                  <el-tag size="small" effect="plain">{{ demo.demo_label }}</el-tag>
                  <el-tag size="small" :type="statusType(demo.status)">
                    {{ statusLabel(demo.status) }}
                  </el-tag>
                </div>
                <RouterLink
                  :to="demo.detail_url"
                  class="block truncate text-lg font-semibold text-slate-900 hover:text-blue-600 dark:text-slate-100 dark:hover:text-blue-300"
                >
                  {{ demo.full_id }}
                </RouterLink>
              </div>
              <div
                class="flex h-11 w-11 flex-none items-center justify-center rounded-lg bg-blue-50 text-blue-500 dark:bg-blue-950/35 dark:text-blue-300"
              >
                <div class="i-carbon-application-web text-2xl" />
              </div>
            </div>

            <div class="space-y-2 text-sm text-gray-500 dark:text-gray-400">
              <div class="flex items-center gap-2">
                <div class="i-carbon-branch" />
                <span>{{ demo.revision || "main" }}</span>
              </div>
              <div v-if="demo.commit_id" class="flex items-center gap-2">
                <div class="i-carbon-commit" />
                <span class="font-mono text-xs">{{ demo.commit_id.slice(0, 7) }}</span>
              </div>
              <div v-if="demo.message" class="line-clamp-2">
                {{ demo.message }}
              </div>
            </div>
          </div>

          <div class="mt-5 flex gap-2">
            <el-button
              type="primary"
              class="flex-1"
              @click="openDemo(demo)"
            >
              <div class="i-carbon-launch mr-1 inline-block" />
              进入演示
            </el-button>
            <el-button @click="$router.push(demo.detail_url)">
              详情
            </el-button>
          </div>
        </article>
      </div>
    </el-skeleton>
  </div>
</template>

<script setup>
import { ElMessage } from "element-plus";
import { runtimeAPI } from "@/utils/api";

const router = useRouter();
const loading = ref(false);
const demos = ref([]);

function statusLabel(status) {
  const labels = {
    running: "运行中",
    starting: "启动中",
    stopped: "已停止",
    error: "异常",
  };
  return labels[status] || status;
}

function statusType(status) {
  if (status === "running") return "success";
  if (status === "starting") return "warning";
  if (status === "error") return "danger";
  return "info";
}

function openDemo(demo) {
  if (demo.proxy_url) {
    window.location.href = demo.proxy_url;
    return;
  }
  router.push(demo.detail_url);
}

async function loadDemos() {
  loading.value = true;
  try {
    const { data } = await runtimeAPI.listDemos();
    demos.value = data.demos || [];
  } catch (err) {
    console.error("Failed to load demos:", err);
    ElMessage.error("加载 Demo 失败");
  } finally {
    loading.value = false;
  }
}

onMounted(loadDemos);
</script>
