<template>
  <header
    class="sticky top-0 z-1000 border-b border-white/10 bg-white/78 dark:bg-slate-950/72 backdrop-blur-xl transition-colors"
  >
    <div class="container-main flex h-15 items-center justify-between gap-4">
      <RouterLink to="/" class="flex min-w-0 items-center gap-3">
        <img
          src="/images/logo-square.png"
          alt="中文开源AI模型社区"
          class="h-9 w-9 rounded-lg shadow-sm"
        />
        <div class="min-w-0">
          <div class="truncate text-base font-bold text-slate-900 dark:text-slate-50">
            中文开源AI模型社区
          </div>
          <div class="truncate text-xs text-slate-500 dark:text-slate-400">
            模型托管 · 数据集 · Demo · 评测
          </div>
        </div>
      </RouterLink>

      <nav
        class="hidden items-center gap-1 rounded-full border border-slate-200/70 bg-white/70 p-1 text-sm shadow-sm dark:border-slate-700/60 dark:bg-slate-900/60 md:flex"
        aria-label="主导航"
      >
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="rounded-full px-4 py-2 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="hidden items-center gap-3 md:flex">
        <el-tooltip content="切换主题" placement="bottom">
          <el-button
            @click="themeStore.toggle()"
            circle
            text
            class="!text-slate-600 dark:!text-slate-300"
          >
            <div v-if="themeStore.isDark" class="i-carbon-moon text-xl" />
            <div v-else class="i-carbon-asleep text-xl" />
          </el-button>
        </el-tooltip>

        <template v-if="isAuthenticated">
          <el-dropdown trigger="click">
            <el-button type="primary" round class="!px-4">
              <div class="i-carbon-add mr-1 text-lg" />
              新建
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="createNew('model')">
                  <div class="flex items-center gap-2">
                    <div class="i-carbon-model text-blue-500" />
                    <span>新建模型</span>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item @click="createNew('dataset')">
                  <div class="flex items-center gap-2">
                    <div class="i-carbon-data-table text-green-500" />
                    <span>新建数据集</span>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item @click="createNew('space')">
                  <div class="flex items-center gap-2">
                    <div class="i-carbon-application text-purple-500" />
                    <span>新建空间</span>
                  </div>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <el-dropdown>
            <div
              class="glass-toolbar flex cursor-pointer items-center gap-2 rounded-full px-3 py-1.5"
            >
              <img
                v-if="hasAvatar"
                :src="`/api/users/${username}/avatar?t=${Date.now()}`"
                :alt="`${username} avatar`"
                class="h-8 w-8 rounded-full border border-slate-200 object-cover dark:border-slate-700"
                @error="hasAvatar = false"
              />
              <div
                v-else
                class="i-carbon-user-avatar text-2xl text-slate-500 dark:text-slate-300"
              />
              <span class="max-w-30 truncate text-sm font-medium">
                {{ username }}
              </span>
              <div class="i-carbon-chevron-down text-slate-400" />
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push(`/${username}`)">
                  <div class="i-carbon-user mr-2 inline-block" />
                  个人主页
                </el-dropdown-item>
                <el-dropdown-item @click="$router.push('/settings')">
                  <div class="i-carbon-settings mr-2 inline-block" />
                  个人设置
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <div class="i-carbon-logout mr-2 inline-block" />
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>

        <template v-else>
          <el-button @click="$router.push('/login')" round plain>
            登录
          </el-button>
          <el-button type="primary" round @click="$router.push('/register')">
            注册
          </el-button>
        </template>
      </div>

      <div class="flex items-center gap-2 md:hidden">
        <el-button
          @click="themeStore.toggle()"
          circle
          text
          size="small"
          class="!text-slate-700 dark:!text-slate-300"
        >
          <div v-if="themeStore.isDark" class="i-carbon-moon text-lg" />
          <div v-else class="i-carbon-asleep text-lg" />
        </el-button>
        <el-button
          @click="mobileMenuOpen = !mobileMenuOpen"
          circle
          text
          class="!min-h-10 !min-w-10 !text-slate-700 dark:!text-slate-300"
        >
          <div class="i-carbon-menu text-2xl" />
        </el-button>
      </div>
    </div>

    <el-drawer
      v-model="mobileMenuOpen"
      direction="rtl"
      size="300px"
      :show-close="false"
    >
      <div class="flex h-full flex-col gap-6">
        <div class="border-b border-slate-200 pb-4 dark:border-slate-800">
          <div class="text-lg font-semibold">导航</div>
          <div class="mt-1 text-sm text-slate-500 dark:text-slate-400">
            浏览资源、管理个人空间或快速创建新项目。
          </div>
        </div>

        <nav class="flex flex-col gap-2" aria-label="移动端导航">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            @click="mobileMenuOpen = false"
            class="rounded-lg px-4 py-3 text-slate-700 transition-colors hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <template v-if="isAuthenticated">
          <div class="border-t border-slate-200 pt-4 dark:border-slate-800">
            <div class="mb-2 px-1 text-xs font-semibold tracking-wide text-slate-500">
              快速创建
            </div>
            <div class="flex flex-col gap-2">
              <button
                v-for="item in createItems"
                :key="item.label"
                class="flex items-center gap-3 rounded-lg px-4 py-3 text-left text-slate-700 transition-colors hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                @click="
                  item.action();
                  mobileMenuOpen = false;
                "
              >
                <div :class="item.icon" />
                <span>{{ item.label }}</span>
              </button>
            </div>
          </div>

          <div class="mt-auto border-t border-slate-200 pt-4 dark:border-slate-800">
            <div class="mb-4 flex items-center gap-3 rounded-lg bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
              <img
                v-if="hasAvatar"
                :src="`/api/users/${username}/avatar?t=${Date.now()}`"
                :alt="`${username} avatar`"
                class="h-11 w-11 rounded-full border border-slate-200 object-cover dark:border-slate-700"
                @error="hasAvatar = false"
              />
              <div
                v-else
                class="flex h-11 w-11 items-center justify-center rounded-full bg-slate-200 dark:bg-slate-800"
              >
                <div class="i-carbon-user-avatar text-2xl text-slate-400" />
              </div>
              <div class="min-w-0">
                <div class="truncate font-medium">{{ username }}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400">
                  已登录
                </div>
              </div>
            </div>

            <div class="flex flex-col gap-2">
              <button
                class="rounded-lg px-4 py-3 text-left text-slate-700 transition-colors hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                @click="
                  $router.push(`/${username}`);
                  mobileMenuOpen = false;
                "
              >
                个人主页
              </button>
              <button
                class="rounded-lg px-4 py-3 text-left text-slate-700 transition-colors hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                @click="
                  $router.push('/settings');
                  mobileMenuOpen = false;
                "
              >
                个人设置
              </button>
              <button
                class="rounded-lg px-4 py-3 text-left text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40"
                @click="
                  handleLogout();
                  mobileMenuOpen = false;
                "
              >
                退出登录
              </button>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="mt-auto flex flex-col gap-3">
            <el-button
              round
              size="large"
              @click="
                $router.push('/login');
                mobileMenuOpen = false;
              "
            >
              登录
            </el-button>
            <el-button
              type="primary"
              round
              size="large"
              @click="
                $router.push('/register');
                mobileMenuOpen = false;
              "
            >
              注册账号
            </el-button>
          </div>
        </template>
      </div>
    </el-drawer>
  </header>
</template>

<script setup>
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useThemeStore } from "@/stores/theme";
import { ElMessage } from "element-plus";

const authStore = useAuthStore();
const themeStore = useThemeStore();
const { isAuthenticated, username } = storeToRefs(authStore);
const router = useRouter();
const mobileMenuOpen = ref(false);
const hasAvatar = ref(true);

const navItems = [
  { to: "/models", label: "模型" },
  { to: "/datasets", label: "数据集" },
  { to: "/spaces", label: "空间" },
  { to: "/leaderboards/generative-llm", label: "排行榜" },
  { to: "/assistant", label: "助手" },
];

function createNew(type) {
  router.push({
    path: "/new",
    query: { type },
  });
}

const createItems = [
  {
    label: "新建模型",
    icon: "i-carbon-model text-blue-500",
    action: () => createNew("model"),
  },
  {
    label: "新建数据集",
    icon: "i-carbon-data-table text-green-500",
    action: () => createNew("dataset"),
  },
  {
    label: "新建空间",
    icon: "i-carbon-application text-purple-500",
    action: () => createNew("space"),
  },
];

async function handleLogout() {
  try {
    await authStore.logout();
    ElMessage.success("已退出登录");
    router.push("/");
  } catch {
    ElMessage.error("退出登录失败");
  }
}
</script>

<style scoped>
@media (max-width: 768px) {
  :deep(.el-button) {
    min-height: 44px;
  }
}
</style>
