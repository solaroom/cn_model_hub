<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router";
import { useAdminStore } from "@/stores/admin";
import { globalSearch } from "@/utils/api";
import { ElMessage } from "element-plus";

const router = useRouter();
const adminStore = useAdminStore();

const dialogVisible = ref(false);
const searchQuery = ref("");
const searchResults = ref(null);
const loading = ref(false);
const searchDebounceTimer = ref(null);
const selectedIndex = ref(0);

const flatResults = computed(() => {
  if (!searchResults.value) return [];

  const results = [];

  if (searchResults.value.results.users) {
    searchResults.value.results.users.forEach((user) => {
      results.push({
        type: "user",
        data: user,
        label: user.username,
        sublabel: user.email,
      });
    });
  }

  if (searchResults.value.results.repositories) {
    searchResults.value.results.repositories.forEach((repo) => {
      results.push({
        type: "repo",
        data: repo,
        label: repo.full_id,
        sublabel: `${repo.repo_type} · ${repo.owner_username}`,
      });
    });
  }

  if (searchResults.value.results.commits) {
    searchResults.value.results.commits.forEach((commit) => {
      results.push({
        type: "commit",
        data: commit,
        label: commit.message,
        sublabel: `${commit.username} · ${commit.commit_id.substring(0, 8)}`,
      });
    });
  }

  return results;
});

const hasResults = computed(() => flatResults.value.length > 0);

function openDialog() {
  dialogVisible.value = true;
  searchQuery.value = "";
  searchResults.value = null;
  selectedIndex.value = 0;
}

function closeDialog() {
  dialogVisible.value = false;
  searchQuery.value = "";
  searchResults.value = null;
}

async function performSearch() {
  if (!searchQuery.value || searchQuery.value.length < 2) {
    searchResults.value = null;
    return;
  }

  loading.value = true;
  try {
    searchResults.value = await globalSearch(
      adminStore.token,
      searchQuery.value,
      ["users", "repos", "commits"],
      10,
    );
    selectedIndex.value = 0;
  } catch (error) {
    console.error("Search failed:", error);
    ElMessage.error("搜索失败，请重试。");
  } finally {
    loading.value = false;
  }
}

function handleSearchInput() {
  if (searchDebounceTimer.value) {
    clearTimeout(searchDebounceTimer.value);
  }

  searchDebounceTimer.value = setTimeout(() => {
    performSearch();
  }, 300);
}

function handleKeyDown(event) {
  if (!hasResults.value) return;

  if (event.key === "ArrowDown") {
    event.preventDefault();
    selectedIndex.value = Math.min(
      selectedIndex.value + 1,
      flatResults.value.length - 1,
    );
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    selectedIndex.value = Math.max(selectedIndex.value - 1, 0);
  } else if (event.key === "Enter") {
    event.preventDefault();
    if (flatResults.value[selectedIndex.value]) {
      handleSelectResult(flatResults.value[selectedIndex.value]);
    }
  }
}

function handleSelectResult(result) {
  closeDialog();

  switch (result.type) {
    case "user":
      router.push("/users");
      ElMessage.success(`已定位到用户：${result.data.username}`);
      break;
    case "repo":
      router.push("/repositories");
      ElMessage.success(`已定位到仓库：${result.data.full_id}`);
      break;
    case "commit":
      router.push("/commits");
      ElMessage.success("已定位到提交记录");
      break;
  }
}

function handleGlobalKeyDown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === "k") {
    event.preventDefault();
    openDialog();
  }

  if (event.key === "Escape" && dialogVisible.value) {
    closeDialog();
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleGlobalKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleGlobalKeyDown);
  if (searchDebounceTimer.value) {
    clearTimeout(searchDebounceTimer.value);
  }
});

watch(dialogVisible, (newVal) => {
  if (newVal) {
    setTimeout(() => {
      const input = document.querySelector(".global-search-input input");
      if (input) input.focus();
    }, 100);
  }
});

defineExpose({ openDialog });
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    width="600px"
    :show-close="false"
    class="global-search-dialog"
  >
    <div class="search-container">
      <el-input
        v-model="searchQuery"
        placeholder="搜索用户、仓库、提交记录……"
        size="large"
        clearable
        @input="handleSearchInput"
        @keydown="handleKeyDown"
        class="global-search-input"
      >
        <template #prefix>
          <div class="i-carbon-search text-xl text-gray-400" />
        </template>
        <template #suffix>
          <div class="flex items-center gap-2">
            <span
              v-if="loading"
              class="i-carbon-circle-dash animate-spin text-gray-400"
            />
            <el-tag size="small" effect="plain">Ctrl+K</el-tag>
          </div>
        </template>
      </el-input>

      <div
        v-if="searchQuery && searchQuery.length >= 2"
        class="results-container"
      >
        <div v-if="loading" class="py-8 text-center text-gray-500">
          <div class="i-carbon-circle-dash mb-2 animate-spin text-2xl" />
          <p>正在搜索...</p>
        </div>

        <div v-else-if="!hasResults" class="py-8 text-center text-gray-500">
          <div class="i-carbon-search-locate mb-2 text-3xl" />
          <p>未找到“{{ searchQuery }}”的结果</p>
        </div>

        <div v-else class="results-list">
          <div
            v-if="
              searchResults?.results?.users &&
              searchResults.results.users.length > 0
            "
            class="result-section"
          >
            <div class="section-header">
              <div class="i-carbon-user text-blue-600" />
              <span>用户（{{ searchResults.results.users.length }}）</span>
            </div>
            <div
              v-for="user in searchResults.results.users"
              :key="`user-${user.id}`"
              class="result-item"
              :class="{
                selected:
                  flatResults[selectedIndex]?.type === 'user' &&
                  flatResults[selectedIndex]?.data.id === user.id,
              }"
              @click="
                handleSelectResult({
                  type: 'user',
                  data: user,
                  label: user.username,
                  sublabel: user.email,
                })
              "
            >
              <div class="i-carbon-user text-blue-600" />
              <div class="result-content">
                <div class="result-label">{{ user.username }}</div>
                <div class="result-sublabel">{{ user.email }}</div>
              </div>
              <el-tag v-if="user.email_verified" type="success" size="small" effect="plain">
                已验证
              </el-tag>
            </div>
          </div>

          <div
            v-if="
              searchResults?.results?.repositories &&
              searchResults.results.repositories.length > 0
            "
            class="result-section"
          >
            <div class="section-header">
              <div class="i-carbon-data-base text-green-600" />
              <span>仓库（{{ searchResults.results.repositories.length }}）</span>
            </div>
            <div
              v-for="repo in searchResults.results.repositories"
              :key="`repo-${repo.id}`"
              class="result-item"
              :class="{
                selected:
                  flatResults[selectedIndex]?.type === 'repo' &&
                  flatResults[selectedIndex]?.data.id === repo.id,
              }"
              @click="
                handleSelectResult({
                  type: 'repo',
                  data: repo,
                  label: repo.full_id,
                  sublabel: `${repo.repo_type} · ${repo.owner_username}`,
                })
              "
            >
              <div class="i-carbon-data-base text-green-600" />
              <div class="result-content">
                <div class="result-label">{{ repo.full_id }}</div>
                <div class="result-sublabel">
                  {{ repo.repo_type }} · {{ repo.owner_username }}
                </div>
              </div>
              <el-tag v-if="repo.private" type="warning" size="small" effect="plain">
                私有
              </el-tag>
            </div>
          </div>

          <div
            v-if="
              searchResults?.results?.commits &&
              searchResults.results.commits.length > 0
            "
            class="result-section"
          >
            <div class="section-header">
              <div class="i-carbon-version text-orange-600" />
              <span>提交（{{ searchResults.results.commits.length }}）</span>
            </div>
            <div
              v-for="commit in searchResults.results.commits"
              :key="`commit-${commit.id}`"
              class="result-item"
              :class="{
                selected:
                  flatResults[selectedIndex]?.type === 'commit' &&
                  flatResults[selectedIndex]?.data.id === commit.id,
              }"
              @click="
                handleSelectResult({
                  type: 'commit',
                  data: commit,
                  label: commit.message,
                  sublabel: `${commit.username} · ${commit.commit_id.substring(0, 8)}`,
                })
              "
            >
              <div class="i-carbon-version text-orange-600" />
              <div class="result-content">
                <div class="result-label">{{ commit.message }}</div>
                <div class="result-sublabel">
                  {{ commit.username }} · {{ commit.commit_id.substring(0, 8) }} ·
                  {{ commit.repo_full_id }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="hint-text">
        <p>请输入至少 2 个字符开始搜索</p>
        <p class="mt-2 text-xs">
          <kbd>↑</kbd> <kbd>↓</kbd> 浏览，<kbd>Enter</kbd> 选择，<kbd>Esc</kbd> 关闭
        </p>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.global-search-dialog :deep(.el-dialog) {
  margin-top: 10vh;
  border-radius: 12px;
  background: var(--admin-surface-strong);
  border: 1px solid var(--admin-border);
  box-shadow: var(--admin-shadow);
}

.global-search-dialog :deep(.el-dialog__header) {
  display: none;
}

.global-search-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.search-container {
  padding: 20px;
}

.global-search-input {
  margin-bottom: 16px;
}

.results-container {
  max-height: 400px;
  overflow-y: auto;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 600;
  color: var(--admin-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  background: rgba(148, 163, 184, 0.08);
  border-radius: 6px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.result-item:hover {
  background: rgba(148, 163, 184, 0.08);
  border-color: var(--admin-border);
}

.result-item.selected {
  background: rgba(37, 99, 235, 0.1);
  border-color: rgba(37, 99, 235, 0.28);
}

.result-content {
  min-width: 0;
  flex: 1;
}

.result-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--admin-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-sublabel {
  font-size: 12px;
  color: var(--admin-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hint-text {
  padding: 40px 20px;
  text-align: center;
  color: var(--admin-text-muted);
}

kbd {
  display: inline-block;
  padding: 3px 8px;
  font-size: 12px;
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid var(--admin-border);
  border-radius: 4px;
  margin: 0 2px;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
