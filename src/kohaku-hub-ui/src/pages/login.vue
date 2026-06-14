<!-- src/kohaku-hub-ui/src/pages/login.vue -->
<template>
  <div class="page-shell flex min-h-[calc(100vh-16rem)] items-center justify-center">
    <div class="card w-full max-w-md">
      <div class="mb-6 text-center">
        <div class="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-300">
          <div class="i-carbon-user-multiple text-2xl" />
        </div>
        <h1 class="text-2xl font-bold">登录 KohakuHub</h1>
        <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">
          使用账号密码进入你的资源空间
        </p>
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
            placeholder="请输入用户名"
            size="large"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          class="w-full"
          :loading="loading"
          @click="handleSubmit"
        >
          登录
        </el-button>
      </el-form>

      <div
        v-if="!siteConfig?.invitation_only"
        class="mt-4 text-center text-sm text-gray-600 dark:text-gray-400"
      >
        还没有账号？
        <RouterLink
          to="/register"
          class="text-blue-500 dark:text-blue-400 hover:underline"
        >
          去注册
        </RouterLink>
      </div>

      <!-- Invitation-only message -->
      <div
        v-else
        class="mt-4 text-center text-sm text-gray-600 dark:text-gray-400"
      >
        <div class="i-carbon-locked inline-block mr-1" />
        当前仅支持邀请注册，如无账号请联系管理员。
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

const form = reactive({
  username: "",
  password: "",
});

const rules = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
  ],
};

async function loadSiteConfig() {
  try {
    const { data } = await axios.get("/api/site-config");
    siteConfig.value = data;
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
      await authStore.login(form);
      ElMessage.success("登录成功");

      // Check for return URL query parameter
      const returnUrl = route.query.return;
      if (returnUrl) {
        router.push(decodeURIComponent(returnUrl));
      } else {
        router.push("/");
      }
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || "登录失败");
    } finally {
      loading.value = false;
    }
  });
}

onMounted(() => {
  loadSiteConfig();
});
</script>
