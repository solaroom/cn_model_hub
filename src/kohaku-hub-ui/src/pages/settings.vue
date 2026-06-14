<!-- src/kohaku-hub-ui/src/pages/settings.vue -->
<template>
  <div class="container-main">
    <h1 class="text-3xl font-bold mb-6">设置</h1>

    <el-tabs v-model="activeTab">
      <!-- Profile -->
      <el-tab-pane label="个人资料" name="profile">
        <div class="max-w-2xl">
          <!-- Avatar Section -->
          <div class="card mb-4">
            <h2 class="text-xl font-semibold mb-4">头像</h2>
            <AvatarUpload
              entity-type="user"
              :entity-name="user?.username"
              :upload-function="settingsAPI.uploadUserAvatar"
              :delete-function="settingsAPI.deleteUserAvatar"
              @uploaded="avatarKey++"
              @deleted="avatarKey++"
            />
          </div>

          <div class="card">
            <h2 class="text-xl font-semibold mb-4">个人信息</h2>
            <el-form label-position="top">
              <el-form-item label="用户名">
                <el-input :value="user?.username" disabled />
              </el-form-item>
              <el-form-item label="邮箱">
                <el-input v-model="profileForm.email" />
                <div
                  v-if="user?.email_verified"
                  class="text-sm text-green-600 mt-1"
                >
                  <div class="i-carbon-checkmark-filled inline-block" />
                  已验证
                </div>
                <div v-else class="text-sm text-yellow-600 mt-1">
                  <div class="i-carbon-warning inline-block" />
                  未验证
                </div>
              </el-form-item>
              <el-form-item label="姓名">
                <el-input
                  v-model="profileForm.full_name"
                  placeholder="请输入姓名"
                />
              </el-form-item>
              <el-form-item label="简介">
                <el-input
                  v-model="profileForm.bio"
                  type="textarea"
                  :rows="3"
                  placeholder="写一句简短的自我介绍"
                  maxlength="500"
                  show-word-limit
                />
              </el-form-item>
              <el-form-item label="网站">
                <el-input
                  v-model="profileForm.website"
                  placeholder="https://example.com"
                />
              </el-form-item>
              <el-form-item label="社交媒体">
                <div class="space-y-2">
                  <el-input
                    v-model="profileForm.social_media.twitter_x"
                    placeholder="Twitter/X 用户名"
                  >
                    <template #prepend>
                      <div class="i-carbon-logo-x w-4 h-4" />
                    </template>
                  </el-input>
                  <el-input
                    v-model="profileForm.social_media.threads"
                    placeholder="Threads 用户名"
                  >
                    <template #prepend>Threads</template>
                  </el-input>
                  <el-input
                    v-model="profileForm.social_media.github"
                    placeholder="GitHub 用户名"
                  >
                    <template #prepend>
                      <div class="i-carbon-logo-github w-4 h-4" />
                    </template>
                  </el-input>
                  <el-input
                    v-model="profileForm.social_media.huggingface"
                    placeholder="HuggingFace 用户名"
                  >
                    <template #prepend>🤗</template>
                  </el-input>
                </div>
              </el-form-item>
              <el-button
                type="primary"
                @click="updateProfile"
                :disabled="!hasProfileChanges"
              >
                保存资料
              </el-button>
            </el-form>
          </div>

          <!-- Organizations -->
          <div class="card mt-4">
            <h2 class="text-xl font-semibold mb-4">组织</h2>
            <div v-if="userOrgs.length > 0" class="space-y-2">
              <div
                v-for="org in userOrgs"
                :key="org.name"
                class="flex items-center justify-between p-3 border rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                @click="goToOrganization(org.name)"
              >
                <div class="flex items-center gap-3">
                  <div class="i-carbon-group text-2xl text-gray-500" />
                  <div>
                    <div class="font-medium">{{ org.name }}</div>
                    <div class="text-sm text-gray-600">
                      {{ org.roleInOrg || org.role }}
                    </div>
                  </div>
                </div>
                <div class="i-carbon-arrow-right" />
              </div>
            </div>
            <div
              v-else
              class="text-center py-8 text-gray-500 dark:text-gray-400"
            >
              你还没有加入任何组织
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- External Tokens -->
      <el-tab-pane label="外部令牌" name="external-tokens">
        <div class="max-w-2xl">
          <div class="card mb-4">
            <h2 class="text-xl font-semibold mb-4">
              外部回退源令牌
            </h2>
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
              你可以为外部回退源单独配置访问令牌，例如 HuggingFace。配置后可访问对应来源中的私有仓库。
            </p>

            <div class="mb-4">
              <h3 class="text-md font-semibold mb-2">可用来源</h3>
              <div
                v-if="availableSources.length === 0"
                class="text-sm text-gray-500"
              >
                当前未配置回退源
              </div>
              <div v-else class="space-y-2">
                <div
                  v-for="source in availableSources"
                  :key="source.url"
                  class="p-3 border border-gray-200 dark:border-gray-700 rounded"
                >
                  <div class="flex items-center justify-between">
                    <div>
                      <div class="font-medium">{{ source.name }}</div>
                      <div class="text-sm text-gray-600 dark:text-gray-400">
                        {{ source.url }}
                      </div>
                    </div>
                    <el-button
                      v-if="!hasTokenForSource(source.url)"
                      size="small"
                      @click="startAddToken(source)"
                    >
                      添加令牌
                    </el-button>
                    <el-button
                      v-else
                      size="small"
                      type="warning"
                      @click="startEditToken(source)"
                    >
                      编辑令牌
                    </el-button>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="externalTokens.length > 0" class="mt-4">
              <h3 class="text-md font-semibold mb-2">已配置的令牌</h3>
              <div class="space-y-2">
                <div
                  v-for="(token, index) in externalTokens"
                  :key="index"
                  class="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded"
                >
                  <div class="flex-1">
                    <div class="font-medium">
                      {{ getSourceName(token.url) }}
                    </div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">
                      {{ token.url }}
                    </div>
                    <div class="text-sm text-gray-500 font-mono mt-1">
                      {{ token.token ? maskToken(token.token) : "***" }}
                    </div>
                  </div>
                  <div class="flex gap-2">
                    <el-button
                      size="small"
                      @click="startEditToken({ url: token.url })"
                    >
                      编辑
                    </el-button>
                    <el-button
                      size="small"
                      type="danger"
                      @click="handleDeleteExternalToken(token.url)"
                    >
                      删除
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- API Tokens -->
      <el-tab-pane label="API 令牌" name="tokens">
        <div class="max-w-2xl">
          <div class="card mb-4">
            <h2 class="text-xl font-semibold mb-4">创建新令牌</h2>
            <div class="flex gap-2">
              <el-input
                v-model="newTokenName"
                placeholder="令牌名称（例如：my-laptop）"
              />
              <el-button type="primary" @click="handleCreateToken">
                创建令牌
              </el-button>
            </div>
          </div>

          <div v-if="newToken" class="card mb-4 bg-yellow-50">
            <h3 class="font-semibold mb-2">新令牌已创建</h3>
            <p class="text-sm text-gray-600 mb-2">
              请立即复制这枚令牌。离开当前页面后将无法再次查看完整内容。
            </p>
            <el-input :value="newToken" readonly class="font-mono">
              <template #append>
                <el-button @click="copyToken">
                  <div class="i-carbon-copy" />
                </el-button>
              </template>
            </el-input>
          </div>

          <div class="card">
            <h2 class="text-xl font-semibold mb-4">有效令牌</h2>
            <div class="space-y-2">
              <div
                v-for="token in tokens"
                :key="token.id"
                class="flex items-center justify-between p-3 border border-gray-200 rounded"
              >
                <div>
                  <div class="font-medium">{{ token.name }}</div>
                  <div class="text-sm text-gray-600">
                    创建于 {{ formatDate(token.created_at) }}
                  </div>
                </div>
                <el-button
                  type="danger"
                  text
                  @click="handleRevokeToken(token.id)"
                >
                  吊销
                </el-button>
              </div>

              <div
                v-if="!tokens || tokens.length === 0"
                class="text-center py-8 text-gray-500"
              >
                暂无有效令牌
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useRouter } from "vue-router";
import { authAPI, settingsAPI } from "@/utils/api";
import { copyToClipboard } from "@/utils/clipboard";
import {
  getExternalTokens,
  addExternalToken,
  removeExternalToken,
} from "@/utils/externalTokens";
import { ElMessage, ElMessageBox } from "element-plus";
import dayjs from "dayjs";
import AvatarUpload from "@/components/profile/AvatarUpload.vue";

const router = useRouter();
const authStore = useAuthStore();
const { user } = storeToRefs(authStore);

const activeTab = ref("profile");
const newTokenName = ref("");
const newToken = ref("");
const tokens = ref([]);
const userOrgs = ref([]);
const avatarKey = ref(0); // Force re-render avatar on upload/delete
const profileForm = ref({
  email: "",
  full_name: "",
  bio: "",
  website: "",
  social_media: {
    twitter_x: "",
    threads: "",
    github: "",
    huggingface: "",
  },
});

// External tokens
const availableSources = ref([]);
const externalTokens = ref([]);

const hasProfileChanges = computed(() => {
  if (!user.value) return false;
  return (
    profileForm.value.email !== user.value.email ||
    profileForm.value.full_name !== (user.value.full_name || "") ||
    profileForm.value.bio !== (user.value.bio || "") ||
    profileForm.value.website !== (user.value.website || "") ||
    JSON.stringify(profileForm.value.social_media) !==
      JSON.stringify(user.value.social_media || {})
  );
});

function formatDate(date) {
  return dayjs(date).format("YYYY-MM-DD");
}

async function loadTokens() {
  try {
    const { data } = await authAPI.listTokens();
    tokens.value = data.tokens;
  } catch (err) {
    console.error("Failed to load tokens:", err);
  }
}

async function loadUserOrgs() {
  try {
    const { data } = await settingsAPI.whoamiV2();
    userOrgs.value = data.orgs || [];
  } catch (err) {
    console.error("Failed to load organizations:", err);
  }
}

async function updateProfile() {
  try {
    await settingsAPI.updateUserSettings(user.value.username, {
      email: profileForm.value.email,
      full_name: profileForm.value.full_name || null,
      bio: profileForm.value.bio || null,
      website: profileForm.value.website || null,
      social_media: profileForm.value.social_media,
    });
    ElMessage.success("个人资料已更新");
    // Refresh user data
    await authStore.fetchUserInfo();
    // Update form with latest data
    loadUserProfile();
  } catch (err) {
    console.error("Failed to update profile:", err);
    ElMessage.error(err.response?.data?.detail || "更新个人资料失败");
  }
}

async function loadUserProfile() {
  if (!user.value) return;

  try {
    const { data } = await settingsAPI.getUserProfile(user.value.username);
    profileForm.value.email = user.value.email;
    profileForm.value.full_name = data.full_name || "";
    profileForm.value.bio = data.bio || "";
    profileForm.value.website = data.website || "";
    profileForm.value.social_media = data.social_media || {
      twitter_x: "",
      threads: "",
      github: "",
      huggingface: "",
    };
  } catch (err) {
    console.error("Failed to load user profile:", err);
  }
}

function goToOrganization(orgName) {
  router.push(`/organizations/${orgName}`);
}

async function handleCreateToken() {
  if (!newTokenName.value) {
    ElMessage.warning("请输入令牌名称");
    return;
  }

  try {
    const { data } = await authAPI.createToken({ name: newTokenName.value });
    newToken.value = data.token;
    newTokenName.value = "";
    await loadTokens();
    ElMessage.success("令牌已创建");
  } catch (err) {
    ElMessage.error("创建令牌失败");
  }
}

async function handleRevokeToken(id) {
  try {
    await ElMessageBox.confirm(
      "此操作会永久删除该令牌，是否继续？",
      "警告",
      { type: "warning" },
    );

    await authAPI.revokeToken(id);
    await loadTokens();
    ElMessage.success("令牌已吊销");
  } catch (err) {
    if (err !== "cancel") {
      ElMessage.error("吊销令牌失败");
    }
  }
}

async function copyToken() {
  const success = await copyToClipboard(newToken.value);
  if (success) {
    ElMessage.success("令牌已复制到剪贴板");
  } else {
    ElMessage.error("复制令牌失败");
  }
}

// External tokens management
async function loadAvailableSources() {
  try {
    const { data } = await authAPI.getAvailableSources();
    availableSources.value = data || [];
  } catch (err) {
    console.error("Failed to load available sources:", err);
  }
}

function loadExternalTokens() {
  externalTokens.value = getExternalTokens();
}

function hasTokenForSource(url) {
  return externalTokens.value.some((t) => t.url === url);
}

function getSourceName(url) {
  const source = availableSources.value.find((s) => s.url === url);
  return source ? source.name : url;
}

function maskToken(token) {
  if (!token || token.length <= 4) return "***";
  return `${token.substring(0, 4)}***`;
}

async function startAddToken(source) {
  const { value: token } = await ElMessageBox.prompt(
    `请输入 ${source.name} 的访问令牌`,
    `为 ${source.name} 添加令牌`,
    {
      confirmButtonText: "添加",
      cancelButtonText: "取消",
      inputPlaceholder: "请输入令牌（例如：hf_xxx）",
      inputType: "password",
    },
  );

  if (token) {
    try {
      // Save to localStorage (for API token users)
      addExternalToken(source.url, token);

      // Save to database (for session-based auth users)
      if (user.value) {
        await authAPI.addExternalToken(user.value.username, source.url, token);
      }

      loadExternalTokens();
      ElMessage.success(`已为 ${source.name} 添加令牌`);
    } catch (err) {
      console.error("Failed to add external token:", err);
      ElMessage.error("添加令牌失败");
    }
  }
}

async function startEditToken(source) {
  const existing = externalTokens.value.find((t) => t.url === source.url);

  const { value: token } = await ElMessageBox.prompt(
    `更新 ${getSourceName(source.url)} 的访问令牌`,
    `编辑令牌`,
    {
      confirmButtonText: "更新",
      cancelButtonText: "取消",
      inputPlaceholder: "请输入新的令牌",
      inputType: "password",
      inputValue: existing?.token || "",
    },
  );

  if (token) {
    try {
      // Save to localStorage (for API token users)
      addExternalToken(source.url, token);

      // Save to database (for session-based auth users)
      if (user.value) {
        await authAPI.addExternalToken(user.value.username, source.url, token);
      }

      loadExternalTokens();
      ElMessage.success("令牌已更新");
    } catch (err) {
      console.error("Failed to update external token:", err);
      ElMessage.error("更新令牌失败");
    }
  }
}

async function handleDeleteExternalToken(url) {
  try {
    await ElMessageBox.confirm(
      `确定删除 ${getSourceName(url)} 的令牌吗？`,
      "确认删除",
      {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
      },
    );

    // Remove from localStorage (for API token users)
    removeExternalToken(url);

    // Remove from database (for session-based auth users)
    if (user.value) {
      try {
        await authAPI.deleteExternalToken(user.value.username, url);
      } catch (err) {
        console.error("Failed to delete from database:", err);
        // Continue anyway - localStorage is already cleared
      }
    }

    loadExternalTokens();
    ElMessage.success("令牌已删除");
  } catch (err) {
    if (err !== "cancel") {
      ElMessage.error("删除令牌失败");
    }
  }
}

onMounted(() => {
  loadUserProfile();
  loadTokens();
  loadUserOrgs();
  loadAvailableSources();
  loadExternalTokens();
});

watch(user, (newUser) => {
  if (newUser) {
    loadUserProfile();
  }
});
</script>
