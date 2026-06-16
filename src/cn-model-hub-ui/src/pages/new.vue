<!-- src/pages/new.vue -->
<template>
  <div class="container-main">
    <div class="max-w-3xl mx-auto">
      <h1 class="text-2xl md:text-3xl font-bold mb-2">新建仓库</h1>
      <p
        class="text-sm md:text-base text-gray-600 dark:text-gray-400 mb-6 md:mb-8"
      >
        仓库用于存放项目文件、版本历史以及后续协作内容。
      </p>

      <div class="card">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleSubmit"
        >
          <!-- Repository Type -->
          <el-form-item label="仓库类型" prop="type">
            <div class="w-full">
              <el-radio-group
                v-model="form.type"
                size="large"
                class="w-full grid grid-cols-1 sm:grid-cols-3 gap-2"
              >
                <el-radio-button value="model">
                  <div class="flex items-center justify-center gap-2 py-2">
                    <div class="i-carbon-model text-xl" />
                    <span>模型</span>
                  </div>
                </el-radio-button>
                <el-radio-button value="dataset">
                  <div class="flex items-center justify-center gap-2 py-2">
                    <div class="i-carbon-data-table text-xl" />
                    <span>数据集</span>
                  </div>
                </el-radio-button>
                <el-radio-button value="space">
                  <div class="flex items-center justify-center gap-2 py-2">
                    <div class="i-carbon-application text-xl" />
                    <span>空间</span>
                  </div>
                </el-radio-button>
              </el-radio-group>
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400 mt-2">
              {{ getTypeDescription(form.type) }}
            </div>
          </el-form-item>

          <!-- Owner -->
          <el-form-item label="归属" prop="owner">
            <el-select
              v-model="form.owner"
              placeholder="选择归属账号"
              size="large"
              class="w-full"
            >
              <el-option :label="current用户" :value="currentUser">
                <div class="flex items-center gap-2">
                  <div class="i-carbon-user-avatar" />
                  <span>{{ currentUser }}</span>
                  <span class="text-xs text-gray-500">（个人）</span>
                </div>
              </el-option>
              <el-option
                v-for="org in userOrgs"
                :key="org.name"
                :label="org.name"
                :value="org.name"
              >
                <div class="flex items-center gap-2">
                  <div class="i-carbon-enterprise" />
                  <span>{{ org.name }}</span>
                  <span class="text-xs text-gray-500">（组织）</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <!-- Repository Name -->
          <el-form-item :label="`${typeLabel}名称`" prop="name">
            <el-input
              v-model="form.name"
              :placeholder="`my-awesome-${form.type}`"
              size="large"
            >
              <template #prepend>
                <span class="text-gray-600">{{ form.owner }}/</span>
              </template>
            </el-input>
            <div class="text-xs text-gray-500 mt-1">
              <div class="i-carbon-information inline-block mr-1" />
              可使用中文、英文、数字、空格和常见符号；不能包含 /、\、?、#
            </div>
          </el-form-item>

          <!-- Visibility -->
          <el-form-item label="可见性">
            <el-radio-group v-model="form.private" size="large">
              <el-radio :value="false" class="mb-3">
                <div class="flex items-start gap-2">
                  <div class="i-carbon-unlocked text-xl text-green-500" />
                  <div>
                    <div class="font-semibold">公开</div>
                    <div class="text-xs text-gray-600 dark:text-gray-400">
                      任何人都可以在互联网上查看这个仓库
                    </div>
                  </div>
                </div>
              </el-radio>
              <el-radio :value="true">
                <div class="flex items-start gap-2">
                  <div class="i-carbon-locked text-xl text-orange-500" />
                  <div>
                    <div class="font-semibold">私有</div>
                    <div class="text-xs text-gray-600 dark:text-gray-400">
                      由你决定谁可以查看并提交到这个仓库
                    </div>
                  </div>
                </div>
              </el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- Actions -->
          <div
            class="flex flex-col-reverse sm:flex-row gap-3 mt-8 pt-6 border-t border-gray-200 dark:border-gray-700"
          >
            <el-button
              size="large"
              @click="$router.back()"
              class="w-full sm:w-auto"
            >
              取消
            </el-button>
            <el-button
              type="primary"
              size="large"
              :loading="creating"
              @click="handleSubmit"
              class="w-full sm:w-auto"
            >
              <div class="i-carbon-add inline-block mr-1" />
              创建{{ typeLabel }}
            </el-button>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { repoAPI } from "@/utils/api";
import { useAuthStore } from "@/stores/auth";
import { ElMessage } from "element-plus";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const { username: currentUser, organizations: userOrgs } =
  storeToRefs(authStore);

const formRef = ref(null);
const creating = ref(false);

const form = reactive({
  type: route.query.type || "model",
  owner: currentUser.value,
  name: "",
  private: false,
});

const rules = {
  type: [
    {
      required: true,
      message: "请选择仓库类型",
      trigger: "change",
    },
  ],
  owner: [
    { required: true, message: "请选择归属账号", trigger: "change" },
  ],
  name: [
    {
      required: true,
      message: "请输入仓库名称",
      trigger: "blur",
    },
    {
      validator: (_rule, value, callback) => {
        const name = String(value || "").trim();
        if (!name) {
          callback(new Error("请输入仓库名称"));
          return;
        }
        if (/[\\/?#]/.test(name)) {
          callback(new Error("名称不能包含 /、\\、?、#"));
          return;
        }
        if (/[\u0000-\u001f\u007f]/.test(name)) {
          callback(new Error("名称不能包含换行或控制字符"));
          return;
        }
        callback();
      },
      trigger: "blur",
    },
  ],
};

const typeLabel = computed(() => {
  const labels = { model: "模型", dataset: "数据集", space: "空间" };
  return labels[form.type] || "仓库";
});

function getTypeDescription(type) {
  const descriptions = {
    model: "用于存储和分享机器学习模型",
    dataset: "用于存储和分享训练、评测所需的数据集",
    space: "用于创建交互式 AI 演示和应用",
  };
  return descriptions[type] || "";
}

async function handleSubmit() {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (!valid) return;

    creating.value = true;
    try {
      // Backend expects:
      // {
      //   type: "model" | "dataset" | "space",
      //   name: string,
      //   organization: string | null,
      //   private: boolean,
      //   sdk: string | null (optional)
      // }
      const payload = {
        type: form.type,
        name: form.name.trim(),
        organization: form.owner !== currentUser.value ? form.owner : null,
        private: form.private,
      };

      const { data } = await repoAPI.create(payload);

      ElMessage.success(`${typeLabel.value}创建成功，请继续上传文件`);

      // Navigate to the new repository
      // Backend returns: { url: string, repo_id: string }
      const repoId = data.repo_id || `${form.owner}/${payload.name}`;
      const [createdNamespace, ...createdNameParts] = repoId.split("/");
      const createdName = createdNameParts.join("/");
      router.push(
        `/${form.type}s/${encodeURIComponent(createdNamespace)}/${encodeURIComponent(
          createdName,
        )}/upload/main`,
      );
    } catch (err) {
      // `POST /api/repos/create` returns a 409 with a top-level `{url,
      // repo_id, error}` body when the repo already exists (HF-compatible
      // exist-ok contract). Read `.error` before falling back to the
      // legacy `.detail` shape so the user sees the actual conflict
      // message instead of a generic "Failed to create ..." toast.
      ElMessage.error(
        err.response?.data?.error ||
          err.response?.data?.detail ||
          `创建${form.type}失败`,
      );
      console.error("Create repository error:", err);
    } finally {
      creating.value = false;
    }
  });
}

// Watch for type changes from query params
watch(
  () => route.query.type,
  (newType) => {
    if (newType && ["model", "dataset", "space"].includes(newType)) {
      form.type = newType;
    }
  },
);
</script>
