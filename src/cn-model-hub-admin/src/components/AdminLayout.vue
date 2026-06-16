<script setup>
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAdminStore } from "@/stores/admin";
import { useThemeStore } from "@/stores/theme";
import { ElMessage } from "element-plus";
import GlobalSearch from "@/components/GlobalSearch.vue";

const router = useRouter();
const route = useRoute();
const adminStore = useAdminStore();
const themeStore = useThemeStore();

const globalSearchRef = ref(null);

function handleLogout() {
  adminStore.logout();
  ElMessage.success("已退出登录");
  router.push("/login");
}

function openGlobalSearch() {
  if (globalSearchRef.value) {
    globalSearchRef.value.openDialog();
  }
}

const menuItems = [
  { path: "/", label: "仪表盘", icon: "i-carbon-dashboard" },
  { path: "/users", label: "用户", icon: "i-carbon-user-multiple" },
  { path: "/invitations", label: "邀请", icon: "i-carbon-email" },
  { path: "/repositories", label: "仓库", icon: "i-carbon-data-base" },
  { path: "/commits", label: "提交", icon: "i-carbon-version" },
  { path: "/storage", label: "存储", icon: "i-carbon-data-volume" },
  { path: "/fallback-sources", label: "回退源", icon: "i-carbon-connect" },
  { path: "/QuotaOverview", label: "配额总览", icon: "i-carbon-meter" },
  { path: "/health", label: "健康状态", icon: "i-carbon-activity" },
  { path: "/cache", label: "缓存", icon: "i-carbon-data-vis-1" },
  { path: "/credentials", label: "凭证", icon: "i-carbon-password" },
  { path: "/DatabaseViewer", label: "数据库", icon: "i-carbon-data-table" },
];
</script>

<template>
  <el-container class="admin-layout">
    <el-aside width="260px" class="sidebar">
      <div class="sidebar-header">
        <div class="flex items-center gap-3">
          <div class="rounded-lg bg-white/16 p-2 text-white">
            <div class="i-carbon-security text-2xl" />
          </div>
          <div>
            <h2 class="text-xl font-bold text-white">管理后台</h2>
            <div class="text-xs text-white/72">中文开源AI模型社区运维控制台</div>
          </div>
        </div>
      </div>

      <el-menu
        :default-active="route.path"
        router
        class="sidebar-menu"
        :background-color="themeStore.isDark ? '#0f172a' : 'transparent'"
        :text-color="themeStore.isDark ? '#cbd5e1' : '#334155'"
        :active-text-color="'#2563eb'"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.path"
          :index="item.path"
        >
          <div :class="item.icon" class="mr-2 text-lg" />
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">
          <div class="page-title-mini">中文开源AI模型社区运维控制台</div>
          <div class="page-subtitle-mini">统一查看用户、仓库、提交、缓存与健康状态。</div>
        </div>

        <div class="header-actions">
          <el-button @click="openGlobalSearch" class="search-button">
            <div class="i-carbon-search text-lg" />
            <span class="ml-2 hidden sm:inline">搜索</span>
            <el-tag size="small" effect="plain" class="ml-2 hidden md:inline">
              Ctrl+K
            </el-tag>
          </el-button>
          <el-button circle @click="themeStore.toggle()" class="mr-1">
            <div v-if="themeStore.isDark" class="i-carbon-moon text-lg" />
            <div v-else class="i-carbon-asleep text-lg" />
          </el-button>
          <el-button type="danger" @click="handleLogout" :icon="'SwitchButton'">
            退出登录
          </el-button>
        </div>
      </el-header>

      <el-main class="main-content">
        <slot />
      </el-main>
    </el-container>

    <GlobalSearch ref="globalSearchRef" />
  </el-container>
</template>

<style scoped>
.admin-layout {
  min-height: 100vh;
}

.sidebar {
  background: var(--admin-surface);
  border-right: 1px solid var(--admin-border);
  box-shadow: var(--admin-shadow-soft);
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(135deg, #0f172a 0%, #2563eb 55%, #0f766e 100%);
}

.sidebar-menu {
  border-right: none;
  padding: 14px 10px;
}

.header {
  background: var(--admin-surface);
  border-bottom: 1px solid var(--admin-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 24px;
  box-shadow: var(--admin-shadow-soft);
}

.header-title {
  min-width: 0;
}

.page-title-mini {
  font-size: 18px;
  font-weight: 700;
  color: var(--admin-text);
}

.page-subtitle-mini {
  font-size: 13px;
  color: var(--admin-text-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-button {
  border-color: var(--admin-border);
  background: rgba(148, 163, 184, 0.08);
}

.main-content {
  min-height: calc(100vh - 60px);
  background: transparent;
}
</style>
