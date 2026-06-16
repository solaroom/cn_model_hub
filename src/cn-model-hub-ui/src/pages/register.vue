<!-- src/cn-model-hub-ui/src/pages/register.vue -->
<template>
  <div class="page-shell flex min-h-[calc(100vh-16rem)] items-center justify-center">
    <!-- Invitation-only blocked -->
    <div
      v-if="siteConfig?.invitation_only && !invitationToken"
      class="card w-full max-w-md text-center"
    >
      <div class="i-carbon-locked text-6xl text-gray-400 mb-4 inline-block" />
      <h1 class="text-2xl font-bold mb-4">仅支持邀请注册</h1>
      <p class="text-gray-600 dark:text-gray-400 mb-6">
        当前站点创建账号需要邀请链接，请联系管理员获取。
      </p>
      <el-button type="primary" @click="$router.push('/login')">
        前往登录
      </el-button>
    </div>

    <!-- Registration form -->
    <div v-else class="card w-full max-w-md">
      <div class="mb-6 text-center">
        <div class="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-300">
          <div class="i-carbon-user-follow text-2xl" />
        </div>
        <h1 class="text-2xl font-bold">创建账号</h1>
        <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">
          注册后即可托管和协作你的资源
        </p>
      </div>

      <!-- Invitation info -->
      <div
        v-if="invitationToken"
        class="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded"
      >
        <div class="flex items-start gap-2 text-sm">
          <div class="i-carbon-email text-blue-600 text-lg" />
          <div>
            <div class="font-semibold text-blue-800 dark:text-blue-200">
              正在使用邀请链接
            </div>
            <div class="text-blue-700 dark:text-blue-300">
              你将通过邀请链接完成注册
            </div>
          </div>
        </div>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请选择用户名"
            size="large"
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="form.email"
            type="email"
            placeholder="your@email.com"
            size="large"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请设置密码"
            size="large"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          class="w-full"
          :loading="loading"
          @click="handleSubmit"
        >
          注册
        </el-button>
      </el-form>

      <div class="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
        已经有账号了？
        <RouterLink
          to="/login"
          class="text-blue-500 dark:text-blue-400 hover:underline"
        >
          去登录
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import axios from "axios";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const formRef = ref(null);
const loading = ref(false);
const siteConfig = ref(null);
const invitationToken = ref(route.query.invitation || null);

const form = reactive({
  username: "",
  email: "",
  password: "",
});

const rules = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    {
      min: 3,
      message: "用户名至少需要 3 个字符",
      trigger: "blur",
    },
  ],
  email: [
    { required: true, message: "请输入邮箱", trigger: "blur" },
    { type: "email", message: "请输入有效邮箱", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    {
      min: 6,
      message: "密码至少需要 6 个字符",
      trigger: "blur",
    },
  ],
};

async function loadSiteConfig() {
  try {
    const { data } = await axios.get("/api/site-config");
    siteConfig.value = data;

    // If invitation-only and no invitation, user shouldn't be here
    if (data.invitation_only && !invitationToken.value) {
      ElMessage.warning("注册需要邀请链接");
    }
  } catch (err) {
    console.error("Failed to load site config:", err);
  }
}

async function handleSubmit() {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (!valid) return;

    loading.value = true;
    try {
      // Add invitation token to registration if present
      const registerData = { ...form };
      if (invitationToken.value) {
        registerData.invitation_token = invitationToken.value;
      }

      const result = await authStore.register(registerData);
      ElMessage.success(result.message || "注册成功");

      // Auto login if email verified
      if (result.email_verified) {
        await authStore.login({
          username: form.username,
          password: form.password,
        });

        // Redirect based on context
        const returnUrl = route.query.return;
        if (returnUrl) {
          router.push(decodeURIComponent(returnUrl));
        } else if (invitationToken.value) {
          // If registered with invitation, redirect to home
          router.push("/");
        } else {
          router.push("/");
        }
      } else {
        router.push("/login");
      }
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || "注册失败");
    } finally {
      loading.value = false;
    }
  });
}

onMounted(() => {
  loadSiteConfig();
});
</script>
