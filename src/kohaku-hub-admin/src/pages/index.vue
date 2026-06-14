<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import AdminLayout from "@/components/AdminLayout.vue";
import StatsCard from "@/components/StatsCard.vue";
import ChartCard from "@/components/ChartCard.vue";
import { useAdminStore } from "@/stores/admin";
import {
  getDetailedStats,
  getTopRepositories,
  getTimeseriesStats,
  getQuotaOverview,
} from "@/utils/api";
import { formatBytes } from "@/utils/api";
import { ElMessage } from "element-plus";

const router = useRouter();
const adminStore = useAdminStore();
const stats = ref(null);
const topRepos = ref([]);
const loading = ref(false);
const timeseriesData = ref(null);
const chartDays = ref(30);
const quotaOverview = ref(null);

async function loadStats() {
  if (!adminStore.token) {
    router.push("/login");
    return;
  }

  loading.value = true;
  try {
    const [statsData, topReposData, timeseriesResult, quotaData] =
      await Promise.all([
        getDetailedStats(adminStore.token),
        getTopRepositories(adminStore.token, 5, "commits"),
        getTimeseriesStats(adminStore.token, chartDays.value),
        getQuotaOverview(adminStore.token),
      ]);

    stats.value = statsData;
    topRepos.value = topReposData.top_repositories;
    timeseriesData.value = timeseriesResult;
    quotaOverview.value = quotaData;
  } catch (error) {
    console.error("Failed to load stats:", error);
    if (error.response?.status === 401 || error.response?.status === 403) {
      ElMessage.error("管理员令牌无效，请重新登录。");
      adminStore.logout();
      router.push("/login");
    } else {
      ElMessage.error(
        error.response?.data?.detail?.error || "加载系统统计失败",
      );
    }
  } finally {
    loading.value = false;
  }
}

const userGrowthChart = computed(() => {
  if (!timeseriesData.value) return null;
  const dates = Object.keys(timeseriesData.value.users_by_day).sort();
  const values = dates.map((date) => timeseriesData.value.users_by_day[date]);
  return {
    labels: dates,
    datasets: [
      {
        label: "新增用户",
        data: values,
        borderColor: "#409EFF",
        backgroundColor: "rgba(64, 158, 255, 0.1)",
        fill: true,
        tension: 0.4,
      },
    ],
  };
});

const repoGrowthChart = computed(() => {
  if (!timeseriesData.value) return null;

  const dates = Object.keys(timeseriesData.value.repositories_by_day).sort();
  const modelData = dates.map(
    (date) => timeseriesData.value.repositories_by_day[date]?.model || 0,
  );
  const datasetData = dates.map(
    (date) => timeseriesData.value.repositories_by_day[date]?.dataset || 0,
  );
  const spaceData = dates.map(
    (date) => timeseriesData.value.repositories_by_day[date]?.space || 0,
  );

  return {
    labels: dates,
    datasets: [
      {
        label: "模型",
        data: modelData,
        borderColor: "#409EFF",
        backgroundColor: "rgba(64, 158, 255, 0.1)",
        fill: true,
      },
      {
        label: "数据集",
        data: datasetData,
        borderColor: "#67C23A",
        backgroundColor: "rgba(103, 194, 58, 0.1)",
        fill: true,
      },
      {
        label: "空间",
        data: spaceData,
        borderColor: "#E6A23C",
        backgroundColor: "rgba(230, 162, 60, 0.1)",
        fill: true,
      },
    ],
  };
});

const commitActivityChart = computed(() => {
  if (!timeseriesData.value) return null;

  const dates = Object.keys(timeseriesData.value.commits_by_day).sort();
  const values = dates.map((date) => timeseriesData.value.commits_by_day[date]);

  return {
    labels: dates,
    datasets: [
      {
        label: "提交",
        data: values,
        borderColor: "#F56C6C",
        backgroundColor: "rgba(245, 108, 108, 0.1)",
        fill: true,
        tension: 0.4,
      },
    ],
  };
});

function getRepoTypeColor(type) {
  switch (type) {
    case "model":
      return "primary";
    case "dataset":
      return "success";
    case "space":
      return "warning";
    default:
      return "info";
  }
}

onMounted(() => {
  loadStats();
});
</script>

<template>
  <AdminLayout>
    <div class="page-container">
      <div class="page-header">
        <div>
          <h1 class="page-title">仪表盘</h1>
          <p class="page-subtitle mt-2">
            快速查看用户、仓库、提交、存储与配额状态。
          </p>
        </div>
      </div>

      <div v-loading="loading" class="metric-grid">
        <StatsCard
          title="总用户数"
          :value="stats?.users?.total || 0"
          :subtitle="`活跃：${stats?.users?.active || 0} | 已验证：${stats?.users?.verified || 0}`"
          icon="i-carbon-user-multiple"
          color="blue"
        />
        <StatsCard
          title="组织数"
          :value="stats?.organizations?.total || 0"
          icon="i-carbon-enterprise"
          color="purple"
        />
        <StatsCard
          title="总仓库数"
          :value="stats?.repositories?.total || 0"
          :subtitle="`模型：${stats?.repositories?.by_type?.model || 0} | 数据集：${stats?.repositories?.by_type?.dataset || 0}`"
          icon="i-carbon-data-base"
          color="green"
        />
        <StatsCard
          title="总提交数"
          :value="stats?.commits?.total || 0"
          icon="i-carbon-version"
          color="orange"
        />
        <StatsCard
          title="总存储"
          :value="formatBytes(stats?.storage?.total_used || 0)"
          :subtitle="`私有：${formatBytes(stats?.storage?.private_used || 0)} | 公开：${formatBytes(stats?.storage?.public_used || 0)}`"
          icon="i-carbon-data-volume"
          color="cyan"
        />
        <StatsCard
          title="LFS 对象"
          :value="stats?.lfs?.total_objects || 0"
          :subtitle="formatBytes(stats?.lfs?.total_size || 0)"
          icon="i-carbon-document"
          color="pink"
        />
      </div>

      <div v-if="timeseriesData" class="charts-grid mb-6">
        <ChartCard
          v-if="userGrowthChart"
          title="用户增长（近 30 天）"
          :labels="userGrowthChart.labels"
          :datasets="userGrowthChart.datasets"
          :height="220"
        />
        <ChartCard
          v-if="repoGrowthChart"
          title="仓库增长（近 30 天）"
          :labels="repoGrowthChart.labels"
          :datasets="repoGrowthChart.datasets"
          :height="220"
        />
        <ChartCard
          v-if="commitActivityChart"
          title="提交活跃度（近 30 天）"
          :labels="commitActivityChart.labels"
          :datasets="commitActivityChart.datasets"
          :height="220"
        />
      </div>

      <el-card
        v-if="
          quotaOverview &&
          (quotaOverview.users_over_quota.length > 0 ||
            quotaOverview.repos_over_quota.length > 0)
        "
        class="mb-6"
      >
        <template #header>
          <div class="flex items-center gap-2">
            <div class="i-carbon-warning text-orange-600" />
            <span class="font-bold">配额警告</span>
            <el-tag type="warning" size="small">
              {{
                quotaOverview.users_over_quota.length +
                quotaOverview.repos_over_quota.length
              }}
            </el-tag>
          </div>
        </template>

        <div v-if="quotaOverview.users_over_quota.length > 0" class="mb-4">
          <h3 class="mb-2 text-sm font-semibold text-red-600">
            超出配额的用户（{{ quotaOverview.users_over_quota.length }}）
          </h3>
          <el-table
            :data="quotaOverview.users_over_quota.slice(0, 5)"
            size="small"
            stripe
          >
            <el-table-column prop="username" label="用户名" width="150" />
            <el-table-column label="私有" width="150" align="right">
              <template #default="{ row }">
                <span :class="{ 'text-red-600 font-semibold': row.private_percentage > 100 }">
                  {{ row.private_percentage }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="公开" width="150" align="right">
              <template #default="{ row }">
                <span :class="{ 'text-red-600 font-semibold': row.public_percentage > 100 }">
                  {{ row.public_percentage }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" align="right">
              <template #default>
                <el-button type="primary" size="small" @click="$router.push('/users')">
                  管理用户
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="quotaOverview.repos_over_quota.length > 0">
          <h3 class="mb-2 text-sm font-semibold text-red-600">
            超出配额的仓库（{{ quotaOverview.repos_over_quota.length }}）
          </h3>
          <el-table
            :data="quotaOverview.repos_over_quota.slice(0, 5)"
            size="small"
            stripe
          >
            <el-table-column label="仓库" min-width="200">
              <template #default="{ row }">
                <el-tag :type="getRepoTypeColor(row.repo_type)" size="small">
                  {{ row.repo_type }}
                </el-tag>
                <span class="ml-2 font-mono text-sm">{{ row.full_id }}</span>
              </template>
            </el-table-column>
            <el-table-column label="使用率" width="120" align="right">
              <template #default="{ row }">
                <span class="text-red-600 font-semibold">
                  {{ row.percentage }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="大小" width="120" align="right">
              <template #default="{ row }">
                {{ formatBytes(row.used_bytes) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" align="right">
              <template #default>
                <el-button type="primary" size="small" @click="$router.push('/repositories')">
                  查看仓库
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <el-card class="mb-6" v-if="stats?.commits?.top_contributors?.length > 0">
        <template #header>
          <span class="font-bold">贡献者排行</span>
        </template>
        <el-table :data="stats.commits.top_contributors" stripe>
          <el-table-column prop="username" label="用户名" />
          <el-table-column label="提交数" width="120" align="right">
            <template #default="{ row }">
              <el-tag type="success">{{ row.commit_count }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="mb-6" v-if="topRepos.length > 0">
        <template #header>
          <span class="font-bold">提交数最多的仓库</span>
        </template>
        <el-table :data="topRepos" stripe>
          <el-table-column label="仓库" min-width="250">
            <template #default="{ row }">
              <div class="flex items-center gap-2">
                <el-tag :type="getRepoTypeColor(row.repo_type)" size="small">
                  {{ row.repo_type }}
                </el-tag>
                <span class="font-mono">{{ row.repo_full_id }}</span>
                <el-tag
                  v-if="row.private"
                  type="warning"
                  size="small"
                  effect="plain"
                >
                  私有
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="提交数" width="120" align="right">
            <template #default="{ row }">
              <el-tag type="success">{{ row.commit_count }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <div class="mt-8">
        <h2 class="mb-4 text-2xl font-bold text-gray-900 dark:text-gray-100">
          快速操作
        </h2>
        <div class="flex flex-wrap gap-4">
          <el-button type="primary" @click="$router.push('/users')" :icon="'User'">
            管理用户
          </el-button>
          <el-button type="success" @click="$router.push('/repositories')" :icon="'DataBase'">
            查看仓库
          </el-button>
          <el-button @click="$router.push('/commits')" :icon="'GitCommit'">
            查看提交
          </el-button>
          <el-button @click="$router.push('/storage')" :icon="'Storage'">
            浏览存储
          </el-button>
          <el-button @click="$router.push('/quotas')" :icon="'DataVolume'">
            管理配额
          </el-button>
          <el-button @click="loadStats" :icon="'Renew'">
            刷新统计
          </el-button>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<style scoped>
.page-container {
  padding: 24px;
}

.stats-grid,
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 24px;
}
</style>
