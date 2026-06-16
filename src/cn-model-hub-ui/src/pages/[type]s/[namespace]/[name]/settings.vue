<!-- src/pages/[type]s/[namespace]/[name]/settings.vue -->
<template>
  <div class="container-main">
    <!-- Breadcrumb Navigation -->
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
          {{
            repoType === "model"
              ? "模型"
              : repoType === "dataset"
                ? "数据集"
                : "空间"
          }}
        </RouterLink>
      </el-breadcrumb-item>
      <el-breadcrumb-item>
        <RouterLink
          :to="`/${route.params.namespace}`"
          class="text-blue-600 dark:text-blue-400 hover:underline"
        >
          {{ route.params.namespace }}
        </RouterLink>
      </el-breadcrumb-item>
      <el-breadcrumb-item>
        <RouterLink
          :to="`/${repoType}s/${route.params.namespace}/${route.params.name}`"
          class="text-blue-600 dark:text-blue-400 hover:underline"
        >
          {{ route.params.name }}
        </RouterLink>
      </el-breadcrumb-item>
      <el-breadcrumb-item>设置</el-breadcrumb-item>
    </el-breadcrumb>

    <h1 class="text-3xl font-bold mb-6">
      仓库设置：{{ route.params.name }}
    </h1>

    <el-tabs v-model="activeTab">
      <!-- General Settings -->
      <el-tab-pane label="通用" name="general">
        <div class="max-w-2xl space-y-6">
          <!-- Visibility -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">可见性</h2>
            <el-form label-position="top">
              <el-form-item label="仓库可见性">
                <div class="visibility-options">
                  <div
                    :class="[
                      'visibility-option',
                      { selected: !settings.private },
                    ]"
                    @click="settings.private = false"
                  >
                    <div class="option-radio">
                      <div
                        :class="[
                          'radio-circle',
                          { checked: !settings.private },
                        ]"
                      >
                        <div v-if="!settings.private" class="radio-dot" />
                      </div>
                    </div>
                    <div class="option-icon">
                      <div class="i-carbon-unlock text-xl" />
                    </div>
                    <div class="option-content">
                      <div class="option-title">公开</div>
                      <div class="option-description">
                        任何人都可以访问和查看这个仓库
                      </div>
                    </div>
                  </div>

                  <div
                    :class="[
                      'visibility-option',
                      { selected: settings.private },
                    ]"
                    @click="settings.private = true"
                  >
                    <div class="option-radio">
                      <div
                        :class="['radio-circle', { checked: settings.private }]"
                      >
                        <div v-if="settings.private" class="radio-dot" />
                      </div>
                    </div>
                    <div class="option-icon">
                      <div class="i-carbon-locked text-xl" />
                    </div>
                    <div class="option-content">
                      <div class="option-title">私有</div>
                      <div class="option-description">
                        仅你和被授权的协作者可以访问
                      </div>
                    </div>
                  </div>
                </div>
              </el-form-item>

              <el-button type="primary" @click="saveGeneralSettings">
                保存修改
              </el-button>
            </el-form>
          </div>

          <!-- Move/Rename Repository -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4 text-warning">
              移动或重命名仓库
            </h2>
            <p class="text-sm text-gray-600 mb-4">
              移动仓库后，旧地址会跳转到新的仓库地址。
            </p>
            <el-form label-position="top">
              <el-form-item
                label="新的仓库 ID（命名空间/仓库名）"
                :error="
                  moveToRepoValidation.available === false
                    ? moveToRepoValidation.message
                    : undefined
                "
              >
                <el-input
                  v-model="moveToRepo"
                  placeholder="例如：my-org/my-new-repo"
                  @input="handleMoveToRepoChange"
                >
                  <template #suffix>
                    <el-icon
                      v-if="moveToRepoValidation.checking"
                      class="is-loading"
                    >
                      <div class="i-carbon-circle-dash" />
                    </el-icon>
                    <el-icon
                      v-else-if="moveToRepoValidation.available === true"
                      style="color: #67c23a"
                    >
                      <div class="i-carbon-checkmark" />
                    </el-icon>
                    <el-icon
                      v-else-if="moveToRepoValidation.available === false"
                      style="color: #f56c6c"
                    >
                      <div class="i-carbon-warning" />
                    </el-icon>
                  </template>
                </el-input>
              </el-form-item>
              <el-button
                type="warning"
                @click="handleMoveRepo"
                :disabled="moveToRepoValidation.available !== true"
              >
                移动仓库
              </el-button>
            </el-form>
          </div>

          <!-- Danger Zone -->
          <div class="card border-2 border-red-500">
            <h2 class="text-xl font-semibold mb-4 text-red-600">危险操作</h2>
            <div class="space-y-4">
              <div>
                <h3 class="font-medium text-orange-600 mb-2">
                  压缩仓库历史
                </h3>
                <p class="text-sm text-gray-600 mb-3">
                  这会清空提交历史并删除旧版本以优化存储，只保留当前文件状态。此操作无法撤销。
                </p>
                <el-button type="warning" @click="handleSquashRepo">
                  压缩仓库
                </el-button>
              </div>

              <div class="pt-4 border-t border-red-300">
                <h3 class="font-medium text-red-600 mb-2">
                  删除这个仓库
                </h3>
                <p class="text-sm text-gray-600 mb-3">
                  删除后会移除仓库文件、历史记录和平台元数据，无法恢复。请确认你真的不再需要它。
                </p>
                <el-button type="danger" @click="handleDeleteRepo">
                  删除仓库
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Branches & Tags -->
      <el-tab-pane label="分支与标签" name="branches">
        <div class="max-w-2xl space-y-6">
          <!-- Branches -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">分支</h2>

            <!-- Create Branch -->
            <div class="mb-6">
              <h3 class="font-medium mb-3">创建新分支</h3>
              <el-form inline>
                <el-form-item label="分支名称">
                  <el-input
                    v-model="newBranch.name"
                    placeholder="my-feature-branch"
                  />
                </el-form-item>
                <el-form-item label="基于版本">
                  <el-input
                    v-model="newBranch.revision"
                    placeholder="main (default)"
                  />
                </el-form-item>
                <el-button type="primary" @click="handleCreateBranch">
                  创建分支
                </el-button>
              </el-form>
            </div>
          </div>

          <!-- Tags -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">标签</h2>

            <!-- Create Tag -->
            <div class="mb-6">
              <h3 class="font-medium mb-3">创建新标签</h3>
              <el-form label-position="top">
                <el-form-item label="标签名称">
                  <el-input v-model="newTag.name" placeholder="v1.0.0" />
                </el-form-item>
                <el-form-item label="基于版本（可选）">
                  <el-input
                    v-model="newTag.revision"
                    placeholder="main (default)"
                  />
                </el-form-item>
                <el-form-item label="说明（可选）">
                  <el-input
                    v-model="newTag.message"
                    type="textarea"
                    placeholder="发布说明..."
                  />
                </el-form-item>
                <el-button type="primary" @click="handleCreateTag">
                  创建标签
                </el-button>
              </el-form>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- LFS Settings -->
      <el-tab-pane label="LFS 设置" name="lfs">
        <div class="max-w-2xl space-y-6">
          <!-- LFS Threshold -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">LFS 阈值</h2>
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
              大于该大小的文件会使用 Git LFS（大文件存储）保存。这个设置会影响上传性能和存储去重。
            </p>
            <div v-if="lfsSettings" class="space-y-4">
              <el-form label-position="top">
                <el-form-item label="阈值模式">
                  <el-radio-group v-model="lfsSettings.threshold_mode">
                    <div class="space-y-2">
                      <el-radio label="server_default">
                        使用服务器默认值
                        <span class="text-sm text-gray-500 dark:text-gray-400">
                          ({{
                            formatSize(
                              lfsSettings.server_defaults.lfs_threshold_bytes,
                            )
                          }})
                        </span>
                      </el-radio>
                      <el-radio label="custom">自定义阈值</el-radio>
                    </div>
                  </el-radio-group>
                </el-form-item>

                <el-form-item
                  v-if="lfsSettings.threshold_mode === 'custom'"
                  label="自定义阈值（MB）"
                >
                  <el-input-number
                    v-model="lfsSettings.threshold_mb"
                    :min="1"
                    :max="10000"
                    :step="1"
                    :precision="0"
                  />
                  <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    最小值：1 MB（机器学习模型建议 5-10 MB）
                  </div>
                </el-form-item>

                <div
                  v-if="lfsSettings.lfs_threshold_bytes_effective"
                  class="text-sm text-gray-600 dark:text-gray-400"
                >
                  <strong>当前使用：</strong>
                  {{ formatSize(lfsSettings.lfs_threshold_bytes_effective) }}
                  ({{
                    lfsSettings.lfs_threshold_bytes_source === "repository"
                      ? "自定义"
                      : "服务器默认值"
                  }})
                </div>
              </el-form>
            </div>
          </div>

          <!-- LFS Keep Versions -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">LFS 版本历史</h2>
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
              每个 LFS 文件保留的历史版本数量。旧版本会被垃圾回收；保留更多版本可以支持更多回滚操作。
            </p>
            <div v-if="lfsSettings" class="space-y-4">
              <el-form label-position="top">
                <el-form-item label="版本保留模式">
                  <el-radio-group v-model="lfsSettings.versions_mode">
                    <div class="space-y-2">
                      <el-radio label="server_default">
                        使用服务器默认值
                        <span class="text-sm text-gray-500 dark:text-gray-400">
                          ({{ lfsSettings.server_defaults.lfs_keep_versions }}
                          个版本)
                        </span>
                      </el-radio>
                      <el-radio label="custom">自定义版本数量</el-radio>
                    </div>
                  </el-radio-group>
                </el-form-item>

                <el-form-item
                  v-if="lfsSettings.versions_mode === 'custom'"
                  label="保留版本数"
                >
                  <el-input-number
                    v-model="lfsSettings.keep_versions"
                    :min="2"
                    :max="9999"
                    :step="1"
                  />
                  <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    最小值：2 个版本（生产环境建议 5-10 个）
                  </div>
                </el-form-item>

                <div
                  v-if="lfsSettings.lfs_keep_versions_effective"
                  class="text-sm text-gray-600 dark:text-gray-400"
                >
                  <strong>当前使用：</strong>
                  {{ lfsSettings.lfs_keep_versions_effective }} 个版本 ({{
                    lfsSettings.lfs_keep_versions_source === "repository"
                      ? "自定义"
                      : "服务器默认值"
                  }})
                </div>
              </el-form>
            </div>
          </div>

          <!-- LFS Suffix Rules -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">LFS 后缀规则</h2>
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
              指定始终使用 LFS 的文件扩展名，不受文件大小影响。适合模型权重等必须按大文件处理的格式。
            </p>
            <div v-if="lfsSettings" class="space-y-4">
              <el-form label-position="top">
                <el-form-item label="后缀规则">
                  <div class="space-y-2">
                    <div
                      v-for="(suffix, index) in lfsSettings.suffix_rules"
                      :key="index"
                      class="flex items-center gap-2"
                    >
                      <el-input
                        v-model="lfsSettings.suffix_rules[index]"
                        placeholder=".safetensors"
                        class="flex-1"
                      />
                      <el-button
                        type="danger"
                        size="small"
                        @click="removeSuffixRule(index)"
                      >
                        <div class="i-carbon-trash-can" />
                      </el-button>
                    </div>
                    <el-button
                      type="primary"
                      size="small"
                      @click="addSuffixRule"
                    >
                      <div class="i-carbon-add inline-block mr-1" />
                      添加后缀规则
                    </el-button>
                  </div>
                  <div class="text-sm text-gray-500 dark:text-gray-400 mt-2">
                    <strong>常见机器学习格式：</strong> .safetensors, .bin,
                    .gguf, .pt, .pth, .onnx, .msgpack
                  </div>
                </el-form-item>

                <div
                  v-if="
                    lfsSettings.lfs_suffix_rules_effective &&
                    lfsSettings.lfs_suffix_rules_effective.length > 0
                  "
                  class="text-sm text-gray-600 dark:text-gray-400"
                >
                  <strong>当前生效：</strong>
                  {{ lfsSettings.lfs_suffix_rules_effective.join(", ") }}
                </div>
              </el-form>
            </div>
          </div>

          <!-- Save Button -->
          <div class="card">
            <el-button
              type="primary"
              @click="saveLfsSettings"
              :loading="savingLfs"
              size="large"
            >
              保存 LFS 设置
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- Storage & Quota -->
      <el-tab-pane label="存储与配额" name="quota">
        <div class="max-w-2xl space-y-6">
          <!-- Storage Usage Card -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">存储用量</h2>
            <div v-if="quotaInfo" class="space-y-4">
              <div>
                <div class="text-sm text-gray-600 dark:text-gray-400 mb-1">
                  当前用量
                </div>
                <div class="text-3xl font-bold">
                  {{ formatSize(quotaInfo.used_bytes) }}
                </div>
                <div
                  v-if="quotaInfo.effective_quota_bytes"
                  class="text-sm text-gray-500 dark:text-gray-400 mt-1"
                >
                  / {{ formatSize(quotaInfo.effective_quota_bytes) }}
                </div>
              </div>

              <div
                v-if="
                  quotaInfo.percentage_used !== null &&
                  quotaInfo.percentage_used !== undefined
                "
              >
                <el-progress
                  :percentage="
                    Math.min(
                      100,
                      Math.round(quotaInfo.percentage_used * 100) / 100,
                    )
                  "
                  :color="getProgressColor(quotaInfo.percentage_used)"
                  :stroke-width="8"
                  :format="(percentage) => `${percentage.toFixed(2)}%`"
                />
              </div>

              <el-button
                @click="handleRecalculateStorage"
                :loading="recalculating"
              >
                <div class="i-carbon-renew inline-block mr-1" />
                重新计算存储用量
              </el-button>
            </div>
            <div v-else class="text-center py-8">
              <el-icon class="is-loading" :size="40">
                <div class="i-carbon-loading" />
              </el-icon>
              <p class="mt-4 text-gray-500 dark:text-gray-400">
                正在加载存储信息...
              </p>
            </div>
          </div>

          <!-- Repository Quota Card -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">仓库配额</h2>
            <div v-if="quotaInfo" class="space-y-4">
              <el-form label-position="top">
                <el-form-item label="存储上限">
                  <el-radio-group v-model="quotaSettings.mode">
                    <div class="space-y-2">
                      <el-radio label="inherit">
                        继承 {{ route.params.namespace }} 的配额
                        <span
                          v-if="quotaInfo.namespace_quota_bytes"
                          class="text-sm text-gray-500"
                        >
                          ({{ formatSize(quotaInfo.namespace_quota_bytes) }})
                        </span>
                        <span v-else class="text-sm text-gray-500">
                          （无限制）
                        </span>
                      </el-radio>
                      <el-radio label="custom">自定义上限</el-radio>
                    </div>
                  </el-radio-group>
                </el-form-item>

                <el-form-item
                  v-if="quotaSettings.mode === 'custom'"
                  label="自定义上限（GB）"
                >
                  <el-input-number
                    v-model="quotaSettings.quota_gb"
                    :min="0"
                    :max="maxQuotaGB"
                    :step="0.1"
                    :precision="2"
                  />
                  <div
                    v-if="quotaInfo.namespace_available_bytes !== null"
                    class="text-sm text-gray-500 dark:text-gray-400 mt-1"
                  >
                    最大可用：{{ formatSize(maxQuotaBytes) }}（来自命名空间）
                  </div>
                  <div
                    v-else
                    class="text-sm text-gray-500 dark:text-gray-400 mt-1"
                  >
                    当前命名空间没有配额限制
                  </div>
                </el-form-item>

                <el-button
                  type="primary"
                  @click="saveQuotaSettings"
                  :loading="savingQuota"
                >
                  保存配额设置
                </el-button>
              </el-form>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from "vue-router";
import { repoAPI, settingsAPI, validationAPI, quotaAPI } from "@/utils/api";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const activeTab = ref("general");
const settings = ref({
  private: false,
});
const moveToRepo = ref("");
const moveToRepoValidation = ref({
  checking: false,
  available: null,
  message: "",
});
const newBranch = ref({
  name: "",
  revision: "",
});
const newTag = ref({
  name: "",
  revision: "",
  message: "",
});
const quotaInfo = ref(null);
const quotaSettings = ref({
  mode: "inherit", // "inherit" or "custom"
  quota_gb: 0,
});
const recalculating = ref(false);
const savingQuota = ref(false);
const lfsSettings = ref(null);
const savingLfs = ref(false);

const repoId = computed(() => `${route.params.namespace}/${route.params.name}`);
const repoType = computed(() => route.params.type);

const maxQuotaBytes = computed(() => {
  if (!quotaInfo.value) return 0;
  // If namespace has unlimited quota, allow any value
  if (quotaInfo.value.namespace_available_bytes === null) {
    return Number.MAX_SAFE_INTEGER / 1000 ** 3; // Very large GB value
  }
  // Add back current repo quota if it exists (we're replacing it)
  let available = quotaInfo.value.namespace_available_bytes;
  if (quotaInfo.value.quota_bytes !== null) {
    available += quotaInfo.value.quota_bytes;
  }
  return available;
});

const maxQuotaGB = computed(() => {
  return Math.floor((maxQuotaBytes.value / 1000 ** 3) * 100) / 100;
});

function formatValidationMessage(message) {
  if (!message) return "";
  if (message === "Repository name is available") return "仓库名称可用";
  if (message === "Name is available") return "名称可用";

  const existingRepo = message.match(/^Repository (.+) already exists$/);
  if (existingRepo) return `仓库 ${existingRepo[1]} 已存在`;

  const normalizedConflict = message.match(
    /^Repository name conflicts with existing repository: (.+) \(case-insensitive\)$/,
  );
  if (normalizedConflict) {
    return `仓库名称和已有仓库 ${normalizedConflict[1]} 冲突（忽略大小写）`;
  }

  return message;
}

async function loadRepoInfo() {
  try {
    const { data } = await repoAPI.getInfo(
      repoType.value,
      route.params.namespace,
      route.params.name,
    );
    settings.value.private = data.private || false;
    moveToRepo.value = repoId.value;
  } catch (err) {
    console.error("Failed to load repo info:", err);
    ElMessage.error("加载仓库信息失败");
  }
}

async function saveGeneralSettings() {
  try {
    await settingsAPI.updateRepoSettings(
      repoType.value,
      route.params.namespace,
      route.params.name,
      {
        private: settings.value.private,
      },
    );
    ElMessage.success("设置已保存");
  } catch (err) {
    console.error("Failed to update settings:", err);
    ElMessage.error("保存设置失败");
  }
}

let validateTimeout = null;
async function handleMoveToRepoChange() {
  // Clear previous timeout
  if (validateTimeout) {
    clearTimeout(validateTimeout);
  }

  const newRepoId = moveToRepo.value.trim();

  // Reset validation state
  moveToRepoValidation.value = {
    checking: false,
    available: null,
    message: "",
  };

  if (!newRepoId) {
    return;
  }

  // Normalize and check if same as current
  const normalizedCurrent = repoId.value.toLowerCase();
  const normalizedNew = newRepoId.toLowerCase();

  if (normalizedCurrent === normalizedNew) {
    moveToRepoValidation.value = {
      checking: false,
      available: false,
      message: "新的仓库 ID 和当前仓库相同",
    };
    return;
  }

  // Check format
  if (!newRepoId.includes("/")) {
    moveToRepoValidation.value = {
      checking: false,
      available: false,
      message: "仓库 ID 必须使用“命名空间/仓库名”的格式",
    };
    return;
  }

  // Debounce validation API call
  validateTimeout = setTimeout(async () => {
    moveToRepoValidation.value.checking = true;

    try {
      const [namespace, name] = newRepoId.split("/");
      const { data } = await validationAPI.checkName({
        name: name,
        namespace: namespace,
        type: repoType.value,
      });

      moveToRepoValidation.value = {
        checking: false,
        available: data.available,
        message: formatValidationMessage(data.message),
      };
    } catch (err) {
      console.error("Name validation failed:", err);
      moveToRepoValidation.value = {
        checking: false,
        available: false,
        message: "校验仓库名称失败",
      };
    }
  }, 500); // 500ms debounce
}

async function handleMoveRepo() {
  if (!moveToRepo.value) {
    ElMessage.warning("请输入新的仓库 ID");
    return;
  }

  // Normalize repository IDs for comparison (lowercase, trim)
  const normalizedCurrent = repoId.value.toLowerCase().trim();
  const normalizedNew = moveToRepo.value.toLowerCase().trim();

  if (normalizedCurrent === normalizedNew) {
    ElMessage.warning("新的仓库 ID 和当前仓库相同");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `这会将仓库移动到 ${moveToRepo.value}，旧链接会跳转到新地址。是否继续？`,
      "移动仓库",
      {
        type: "warning",
        confirmButtonText: "移动",
        cancelButtonText: "取消",
      },
    );

    await settingsAPI.moveRepo({
      fromRepo: repoId.value,
      toRepo: moveToRepo.value,
      type: repoType.value,
    });

    ElMessage.success("仓库已移动");

    // Redirect to new location
    const [newNamespace, newName] = moveToRepo.value.split("/");
    router.push(`/${repoType.value}s/${newNamespace}/${newName}`);
  } catch (err) {
    if (err !== "cancel") {
      console.error("Failed to move repository:", err);
      const errorMsg =
        err.response?.data?.detail?.error || "移动仓库失败";
      ElMessage.error(errorMsg);
    }
  }
}

async function handleSquashRepo() {
  try {
    await ElMessageBox.confirm(
      `这会清空 ${repoId.value} 的全部提交历史并优化存储，只保留当前状态。此操作无法撤销！`,
      "压缩仓库历史",
      {
        type: "warning",
        confirmButtonText: "压缩",
        cancelButtonText: "取消",
      },
    );

    // Second confirmation
    await ElMessageBox.prompt(
      `请输入仓库名 "${route.params.name}" 进行确认`,
      "确认压缩",
      {
        confirmButtonText: "压缩",
        cancelButtonText: "取消",
        inputPattern: new RegExp(`^${route.params.name}$`),
        inputErrorMessage: "仓库名称不匹配",
      },
    );

    const loading = ElMessage({
      message: "正在压缩仓库历史，可能需要几分钟...",
      type: "info",
      duration: 0,
    });

    try {
      await settingsAPI.squashRepo({
        repo: repoId.value,
        type: repoType.value,
      });

      loading.close();
      ElMessage.success("仓库历史已压缩");

      // Reload page to show updated state
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (err) {
      loading.close();
      throw err;
    }
  } catch (err) {
    if (err !== "cancel" && err !== "close") {
      console.error("Failed to squash repository:", err);
      const errorMsg =
        err.response?.data?.detail?.error || "压缩仓库失败";
      ElMessage.error(errorMsg);
    }
  }
}

async function handleDeleteRepo() {
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${repoId.value} 吗？仓库文件、历史记录和平台元数据都会被删除，且无法恢复！`,
      "删除仓库",
      {
        type: "error",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        confirmButtonClass: "el-button--danger",
      },
    );

    // Second confirmation
    await ElMessageBox.prompt(
      `请输入仓库名 "${route.params.name}" 进行确认`,
      "确认删除",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        inputPattern: new RegExp(`^${route.params.name}$`),
        inputErrorMessage: "仓库名称不匹配",
      },
    );

    await repoAPI.delete({
      type: repoType.value,
      name: route.params.name,
      organization: route.params.namespace,
    });

    ElMessage.success("仓库已删除");
    router.push("/");
  } catch (err) {
    if (err !== "cancel" && err !== "close") {
      console.error("Failed to delete repository:", err);
      const errorMsg =
        err.response?.data?.detail?.error || "删除仓库失败，请确认你有删除权限";
      ElMessage.error(errorMsg);
    }
  }
}

async function handleCreateBranch() {
  if (!newBranch.value.name) {
    ElMessage.warning("请输入分支名称");
    return;
  }

  try {
    await settingsAPI.createBranch(
      repoType.value,
      route.params.namespace,
      route.params.name,
      {
        branch: newBranch.value.name,
        revision: newBranch.value.revision || undefined,
      },
    );

    ElMessage.success(`分支“${newBranch.value.name}”已创建`);
    newBranch.value = { name: "", revision: "" };
  } catch (err) {
    console.error("Failed to create branch:", err);
    ElMessage.error("创建分支失败");
  }
}

async function handleCreateTag() {
  if (!newTag.value.name) {
    ElMessage.warning("请输入标签名称");
    return;
  }

  try {
    await settingsAPI.createTag(
      repoType.value,
      route.params.namespace,
      route.params.name,
      {
        tag: newTag.value.name,
        revision: newTag.value.revision || undefined,
        message: newTag.value.message || undefined,
      },
    );

    ElMessage.success(`标签“${newTag.value.name}”已创建`);
    newTag.value = { name: "", revision: "", message: "" };
  } catch (err) {
    console.error("Failed to create tag:", err);
    ElMessage.error("创建标签失败");
  }
}

async function loadQuotaInfo() {
  try {
    const { data } = await quotaAPI.getRepoQuota(
      repoType.value,
      route.params.namespace,
      route.params.name,
    );
    quotaInfo.value = data;

    // Set initial quota settings based on current quota
    if (data.quota_bytes === null) {
      quotaSettings.value.mode = "inherit";
      quotaSettings.value.quota_gb = 0;
    } else {
      quotaSettings.value.mode = "custom";
      quotaSettings.value.quota_gb =
        Math.round((data.quota_bytes / 1000 ** 3) * 100) / 100;
    }
  } catch (err) {
    console.error("Failed to load quota info:", err);
    ElMessage.error("加载配额信息失败");
  }
}

async function handleRecalculateStorage() {
  recalculating.value = true;
  try {
    const { data } = await quotaAPI.recalculateRepoStorage(
      repoType.value,
      route.params.namespace,
      route.params.name,
    );
    quotaInfo.value = data;
    ElMessage.success("存储用量已重新计算");
  } catch (err) {
    console.error("Failed to recalculate storage:", err);
    const errorMsg =
      err.response?.data?.detail?.error || "重新计算存储用量失败";
    ElMessage.error(errorMsg);
  } finally {
    recalculating.value = false;
  }
}

async function saveQuotaSettings() {
  savingQuota.value = true;
  try {
    const quota_bytes =
      quotaSettings.value.mode === "inherit"
        ? null
        : Math.floor(quotaSettings.value.quota_gb * 1000 ** 3);

    const { data } = await quotaAPI.setRepoQuota(
      repoType.value,
      route.params.namespace,
      route.params.name,
      { quota_bytes },
    );

    quotaInfo.value = data;
    ElMessage.success("配额设置已保存");
  } catch (err) {
    console.error("Failed to save quota settings:", err);
    const errorMsg =
      err.response?.data?.detail?.error || "保存配额设置失败";
    ElMessage.error(errorMsg);
  } finally {
    savingQuota.value = false;
  }
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  if (bytes < 1000) return bytes + " B";
  if (bytes < 1000 * 1000) return (bytes / 1000).toFixed(1) + " KB";
  if (bytes < 1000 * 1000 * 1000)
    return (bytes / (1000 * 1000)).toFixed(1) + " MB";
  return (bytes / (1000 * 1000 * 1000)).toFixed(2) + " GB";
}

function getProgressColor(percentage) {
  if (percentage >= 90) return "#f56c6c"; // Red
  if (percentage >= 75) return "#e6a23c"; // Orange
  return "#67c23a"; // Green
}

async function loadLfsSettings() {
  try {
    const { data } = await settingsAPI.getLfsSettings(
      repoType.value,
      route.params.namespace,
      route.params.name,
    );

    // Initialize local state from API response
    lfsSettings.value = {
      // Server defaults
      server_defaults: data.server_defaults,

      // Configured values
      lfs_threshold_bytes: data.lfs_threshold_bytes,
      lfs_keep_versions: data.lfs_keep_versions,
      lfs_suffix_rules: data.lfs_suffix_rules,

      // Effective values (for display)
      lfs_threshold_bytes_effective: data.lfs_threshold_bytes_effective,
      lfs_threshold_bytes_source: data.lfs_threshold_bytes_source,
      lfs_keep_versions_effective: data.lfs_keep_versions_effective,
      lfs_keep_versions_source: data.lfs_keep_versions_source,
      lfs_suffix_rules_effective: data.lfs_suffix_rules_effective,
      lfs_suffix_rules_source: data.lfs_suffix_rules_source,

      // UI state
      threshold_mode:
        data.lfs_threshold_bytes === null ? "server_default" : "custom",
      threshold_mb: data.lfs_threshold_bytes
        ? Math.round(data.lfs_threshold_bytes / (1000 * 1000))
        : 5,
      versions_mode:
        data.lfs_keep_versions === null ? "server_default" : "custom",
      keep_versions: data.lfs_keep_versions || 5,
      suffix_rules: data.lfs_suffix_rules || [],
    };
  } catch (err) {
    console.error("Failed to load LFS settings:", err);
    ElMessage.error("加载 LFS 设置失败");
  }
}

async function saveLfsSettings() {
  savingLfs.value = true;
  try {
    const payload = {};

    // Threshold
    if (lfsSettings.value.threshold_mode === "custom") {
      payload.lfs_threshold_bytes =
        lfsSettings.value.threshold_mb * 1000 * 1000;
    } else {
      payload.lfs_threshold_bytes = null; // Use server default
    }

    // Keep versions
    if (lfsSettings.value.versions_mode === "custom") {
      payload.lfs_keep_versions = lfsSettings.value.keep_versions;
    } else {
      payload.lfs_keep_versions = null; // Use server default
    }

    // Suffix rules (filter out empty strings)
    const cleanedRules = lfsSettings.value.suffix_rules.filter(
      (r) => r && r.trim(),
    );
    payload.lfs_suffix_rules = cleanedRules.length > 0 ? cleanedRules : null;

    await settingsAPI.updateRepoSettings(
      repoType.value,
      route.params.namespace,
      route.params.name,
      payload,
    );

    ElMessage.success("LFS 设置已保存");

    // Reload to show updated effective values
    await loadLfsSettings();
  } catch (err) {
    console.error("Failed to save LFS settings:", err);
    const errorMsg =
      err.response?.data?.detail?.error || "保存 LFS 设置失败";
    ElMessage.error(errorMsg);
  } finally {
    savingLfs.value = false;
  }
}

function addSuffixRule() {
  lfsSettings.value.suffix_rules.push("");
}

function removeSuffixRule(index) {
  lfsSettings.value.suffix_rules.splice(index, 1);
}

watch(
  () => activeTab.value,
  (newTab) => {
    if (newTab === "quota" && !quotaInfo.value) {
      loadQuotaInfo();
    }
    if (newTab === "lfs" && !lfsSettings.value) {
      loadLfsSettings();
    }
  },
);

onMounted(() => {
  if (!authStore.isAuthenticated) {
    ElMessage.error("请先登录后再访问设置页面");
    router.push("/login");
    return;
  }
  loadRepoInfo();
  // Load quota info if starting on quota tab
  if (activeTab.value === "quota") {
    loadQuotaInfo();
  }
  // Load LFS settings if starting on LFS tab
  if (activeTab.value === "lfs") {
    loadLfsSettings();
  }
});
</script>

<style scoped>
/* Visibility options container */
.visibility-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

/* Individual visibility option */
.visibility-option {
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 0.75rem;
  align-items: start;
  padding: 1rem;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dark .visibility-option {
  border-color: #374151;
}

.visibility-option:hover {
  background-color: #f9fafb;
  border-color: #d1d5db;
}

.dark .visibility-option:hover {
  background-color: #1f2937;
  border-color: #4b5563;
}

.visibility-option.selected {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.dark .visibility-option.selected {
  border-color: #60a5fa;
  background-color: #1e3a8a;
}

/* Custom radio circle */
.option-radio {
  display: flex;
  align-items: center;
  padding-top: 0.125rem;
}

.radio-circle {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid #d1d5db;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.dark .radio-circle {
  border-color: #6b7280;
}

.radio-circle.checked {
  border-color: #3b82f6;
  background-color: #3b82f6;
}

.dark .radio-circle.checked {
  border-color: #60a5fa;
  background-color: #60a5fa;
}

.radio-dot {
  width: 0.5rem;
  height: 0.5rem;
  background-color: white;
  border-radius: 50%;
}

/* Icon styling */
.option-icon {
  display: flex;
  align-items: center;
  color: #6b7280;
  padding-top: 0.125rem;
}

.dark .option-icon {
  color: #9ca3af;
}

.visibility-option.selected .option-icon {
  color: #3b82f6;
}

.dark .visibility-option.selected .option-icon {
  color: #60a5fa;
}

/* Content area */
.option-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.option-title {
  font-weight: 600;
  font-size: 0.9375rem;
  color: #111827;
  line-height: 1.4;
}

.dark .option-title {
  color: #f9fafb;
}

.option-description {
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1.4;
}

.dark .option-description {
  color: #9ca3af;
}
</style>
