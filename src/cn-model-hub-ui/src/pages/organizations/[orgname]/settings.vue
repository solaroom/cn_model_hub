<!-- src/pages/organizations/[orgname]/settings.vue -->
<template>
  <div class="container-main">
    <h1 class="text-3xl font-bold mb-6">
      组织设置： {{ route.params.orgname }}
    </h1>

    <el-tabs v-model="activeTab">
      <!-- General Settings -->
      <el-tab-pane label="通用" name="general">
        <div class="max-w-2xl">
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">基本信息</h2>
            <el-form label-position="top">
              <el-form-item label="组织名称">
                <el-input :value="route.params.orgname" disabled />
              </el-form-item>
              <el-form-item label="描述">
                <el-input
                  v-model="orgSettings.description"
                  type="textarea"
                  :rows="3"
                  placeholder="描述你的组织..."
                />
              </el-form-item>
              <el-button type="primary" @click="saveGeneralSettings">
                保存更改
              </el-button>
            </el-form>
          </div>
        </div>
      </el-tab-pane>

      <!-- Members -->
      <el-tab-pane label="成员" name="members">
        <div class="max-w-2xl">
          <!-- Add Member -->
          <div class="card mb-4">
            <h2 class="text-xl font-semibold mb-4">添加成员</h2>
            <el-form inline>
              <el-form-item label="用户名">
                <el-input v-model="newMember.username" placeholder="username" />
              </el-form-item>
              <el-form-item label="Role">
                <el-select v-model="newMember.role">
                  <el-option label="成员" value="member" />
                  <el-option label="管理员" value="admin" />
                  <el-option label="超级管理员" value="super-admin" />
                </el-select>
              </el-form-item>
              <el-button type="primary" @click="handleAddMember">
                添加成员
              </el-button>
            </el-form>
          </div>

          <!-- Members List -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">当前成员</h2>
            <div v-if="members.length > 0" class="space-y-2">
              <div
                v-for="member in members"
                :key="member.user"
                class="flex items-center justify-between p-3 border rounded"
              >
                <div class="flex items-center gap-3">
                  <div class="i-carbon-user-avatar text-2xl text-gray-500" />
                  <div>
                    <div class="font-medium">{{ member.user }}</div>
                    <div class="text-sm text-gray-600">{{ member.role }}</div>
                  </div>
                </div>
                <div class="flex gap-2">
                  <el-dropdown
                    @command="(role) => handleUpdateRole(成员, role)"
                  >
                    <el-button size="small" type="primary">
                      修改角色
                      <div class="i-carbon-chevron-down ml-1" />
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="member">
                          成员
                        </el-dropdown-item>
                        <el-dropdown-item command="admin">
                          管理员
                        </el-dropdown-item>
                        <el-dropdown-item command="super-admin">
                          超级管理员
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                  <el-button
                    size="small"
                    type="danger"
                    text
                    @click="handleRemoveMember(member)"
                  >
                    Remove
                  </el-button>
                </div>
              </div>
            </div>
            <div
              v-else
              class="text-center py-8 text-gray-500 dark:text-gray-400"
            >
              No members yet
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from "vue-router";
import { orgAPI } from "@/utils/api";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const activeTab = ref("general");
const orgSettings = ref({
  description: "",
});
const members = ref([]);
const newMember = ref({
  username: "",
  role: "member",
});

async function loadOrgInfo() {
  try {
    const { data } = await orgAPI.get(route.params.orgname);
    orgSettings.value.description = data.description || "";
  } catch (err) {
    console.error("Failed to load org info:", err);
    ElMessage.error("Failed to load organization information");
  }
}

async function loadMembers() {
  try {
    const { data } = await orgAPI.listMembers(route.params.orgname);
    members.value = data.members || [];
  } catch (err) {
    console.error("Failed to load members:", err);
    ElMessage.error("Failed to load members");
  }
}

async function saveGeneralSettings() {
  try {
    await orgAPI.updateSettings(route.params.orgname, {
      description: orgSettings.value.description,
    });
    ElMessage.success("Settings updated successfully");
  } catch (err) {
    console.error("Failed to update settings:", err);
    ElMessage.error("Failed to update settings");
  }
}

async function handleAddMember() {
  if (!newMember.value.username) {
    ElMessage.warning("Please enter a username");
    return;
  }

  try {
    await orgAPI.addMember(route.params.orgname, {
      username: newMember.value.username,
      role: newMember.value.role,
    });
    ElMessage.success(`Added ${newMember.value.username} to organization`);
    newMember.value = { username: "", role: "member" };
    await loadMembers();
  } catch (err) {
    console.error("Failed to add member:", err);
    ElMessage.error("Failed to add member");
  }
}

async function handleUpdateRole(member, newRole) {
  if (member.role === newRole) {
    return;
  }

  try {
    await orgAPI.updateMemberRole(route.params.orgname, member.user, {
      role: newRole,
    });
    ElMessage.success(`Updated ${member.user}'s role to ${newRole}`);
    await loadMembers();
  } catch (err) {
    console.error("Failed to update role:", err);
    ElMessage.error("Failed to update role");
  }
}

async function handleRemoveMember(member) {
  try {
    await ElMessageBox.confirm(
      `Remove ${member.user} from the organization?`,
      "Remove Member",
      {
        type: "warning",
        confirmButtonText: "Remove",
        cancelButtonText: "Cancel",
      },
    );

    await orgAPI.removeMember(route.params.orgname, member.user);
    ElMessage.success(`Removed ${member.user} from organization`);
    await loadMembers();
  } catch (err) {
    if (err !== "cancel") {
      console.error("Failed to remove member:", err);
      ElMessage.error("Failed to remove member");
    }
  }
}

onMounted(() => {
  if (!authStore.isAuthenticated) {
    ElMessage.error("You must be logged in to access settings");
    router.push("/login");
    return;
  }
  loadOrgInfo();
  loadMembers();
});
</script>
