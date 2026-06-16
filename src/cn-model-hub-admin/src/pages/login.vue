<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAdminStore } from "@/stores/admin";
import { ElMessage } from "element-plus";

const router = useRouter();
const adminStore = useAdminStore();

const tokenInput = ref("");
const loading = ref(false);

async function handleLogin() {
  if (!tokenInput.value) {
    ElMessage.error("请输入管理员令牌");
    return;
  }

  loading.value = true;

  try {
    const success = await adminStore.login(tokenInput.value);
    if (success) {
      ElMessage.success("登录成功");
      router.push("/");
    } else {
      ElMessage.error("管理员令牌无效");
      tokenInput.value = "";
    }
  } catch (error) {
    console.error("Login error:", error);
    ElMessage.error(error.response?.data?.detail?.error || "登录失败");
    tokenInput.value = "";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="hero-icon">
          <div class="i-carbon-security text-4xl text-white" />
        </div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
          中文开源AI模型社区管理后台
        </h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          输入管理员令牌，进入运维控制台。
        </p>
      </div>

      <el-form @submit.prevent="handleLogin" class="login-form">
        <el-form-item>
          <el-input
            v-model="tokenInput"
            type="password"
            placeholder="请输入管理员令牌"
            size="large"
            :prefix-icon="'Lock'"
            show-password
            autocomplete="off"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          native-type="submit"
          class="w-full"
        >
          {{ loading ? "正在验证..." : "登录后台" }}
        </el-button>
      </el-form>

      <div class="login-footer">
        <el-alert type="info" :closable="false" show-icon>
          <p class="text-sm">
            管理员令牌通常位于环境变量
            <code>CN_MODEL_HUB_ADMIN_SECRET_TOKEN</code>
            中。
          </p>
        </el-alert>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top, rgba(56, 189, 248, 0.22), transparent 28%),
    linear-gradient(135deg, #0f172a 0%, #1d4ed8 52%, #0f766e 100%);
}

.login-card {
  width: 100%;
  max-width: 460px;
  padding: 40px;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 28px 60px rgba(15, 23, 42, 0.24);
  backdrop-filter: blur(18px);
}

html.dark .login-card {
  background: rgba(15, 23, 42, 0.88);
}

.login-header {
  margin-bottom: 28px;
  text-align: center;
}

.hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 16px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #1d4ed8 0%, #0f766e 100%);
  box-shadow: 0 16px 30px rgba(37, 99, 235, 0.24);
}

.login-form {
  margin-bottom: 22px;
}

.login-footer code {
  display: inline-block;
  margin: 0 4px;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.12);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 12px;
}
</style>
