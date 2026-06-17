<template>
  <div class="page-shell">
    <section class="container-main">
      <div class="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <div class="stat-chip mb-3">
            <div class="i-carbon-ai-results" />
            智能助手
          </div>
          <h1 class="section-title">平台问答与资源搜索</h1>
        </div>
        <div class="flex flex-wrap gap-2">
          <el-button round @click="useExample('怎么上传模型并创建 Demo？')">
            模型 Demo
          </el-button>
          <el-button round @click="useExample('帮我找 Qwen2.5 0.5B 的模型')">
            找模型
          </el-button>
          <el-button round @click="useExample('MLflow 和 LakeFS 分别是做什么的？')">
            MLOps
          </el-button>
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <section class="card flex min-h-[68vh] flex-col p-0">
          <div class="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="font-semibold">对话</div>
                <div class="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  {{ statusLine }}
                </div>
              </div>
              <el-button circle :loading="statusLoading" @click="loadStatus">
                <div class="i-carbon-renew" />
              </el-button>
            </div>
          </div>

          <div ref="messagesEl" class="flex-1 space-y-5 overflow-y-auto px-5 py-5">
            <div
              v-for="message in messages"
              :key="message.id"
              class="flex"
              :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
            >
              <div
                class="max-w-[92%] rounded-lg border px-4 py-3 shadow-sm md:max-w-[78%]"
                :class="
                  message.role === 'user'
                    ? 'border-blue-500 bg-blue-600 text-white'
                    : 'border-slate-200 bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'
                "
              >
                <div class="mb-2 flex items-center gap-2 text-xs opacity-80">
                  <div
                    :class="
                      message.role === 'user'
                        ? 'i-carbon-user'
                        : 'i-carbon-ai-status-complete'
                    "
                  />
                  <span>{{ message.role === "user" ? "用户问题" : "Agent 回答" }}</span>
                  <span v-if="message.intent" class="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    {{ intentLabel(message.intent) }}
                  </span>
                </div>

                <MarkdownViewer
                  v-if="message.role === 'assistant'"
                  :content="message.content"
                  :strip-frontmatter="false"
                  class="assistant-markdown"
                />
                <div v-else class="whitespace-pre-wrap break-words">
                  {{ message.content }}
                </div>

                <div v-if="message.loading" class="mt-3 flex items-center gap-2 text-sm opacity-80">
                  <el-icon class="is-loading">
                    <div class="i-carbon-loading" />
                  </el-icon>
                  正在生成
                </div>
              </div>
            </div>
          </div>

          <form
            class="border-t border-slate-200 p-4 dark:border-slate-800"
            @submit.prevent="send"
          >
            <div class="flex flex-col gap-3 md:flex-row">
              <el-input
                v-model="question"
                type="textarea"
                :rows="2"
                maxlength="1000"
                show-word-limit
                resize="none"
                placeholder="输入问题"
                @keydown.enter.exact.prevent="send"
              />
              <el-button
                type="primary"
                native-type="submit"
                :loading="sending"
                class="!h-auto !min-w-24"
              >
                <div class="i-carbon-send mr-1" />
                发送
              </el-button>
            </div>
          </form>
        </section>

        <aside class="space-y-4">
          <section class="card">
            <div class="mb-3 flex items-center gap-2 font-semibold">
              <div class="i-carbon-flow-logs-vpc text-blue-500" />
              Agent 判断
            </div>
            <div v-if="lastResponse" class="space-y-3 text-sm">
              <div class="flex items-center justify-between gap-3">
                <span class="text-slate-500 dark:text-slate-400">意图</span>
                <span class="font-medium">{{ intentLabel(lastResponse.intent) }}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="text-slate-500 dark:text-slate-400">搜索</span>
                <span class="font-medium">{{ lastResponse.search?.backend || "未调用" }}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="text-slate-500 dark:text-slate-400">RAG</span>
                <span class="font-medium">{{ lastResponse.rag?.mode || "未调用" }}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="text-slate-500 dark:text-slate-400">大模型</span>
                <span class="font-medium">{{ lastResponse.llm?.provider || "-" }}</span>
              </div>
            </div>
            <div v-else class="text-sm text-slate-500 dark:text-slate-400">
              等待提问
            </div>
          </section>

          <section class="card">
            <div class="mb-3 flex items-center gap-2 font-semibold">
              <div class="i-carbon-search-locate text-emerald-500" />
              平台结果
            </div>
            <div v-if="searchResults.length" class="space-y-3">
              <RouterLink
                v-for="item in searchResults"
                :key="`${item.type}:${item.id}`"
                :to="item.url"
                class="block rounded-lg border border-slate-200 p-3 transition-colors hover:border-blue-300 hover:bg-blue-50/60 dark:border-slate-700 dark:hover:border-blue-500 dark:hover:bg-blue-950/25"
              >
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0">
                    <div class="truncate font-medium text-blue-600 dark:text-blue-400">
                      {{ item.title }}
                    </div>
                    <div class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {{ item.type_label }} · {{ item.author }}
                    </div>
                  </div>
                  <div class="i-carbon-arrow-up-right shrink-0 text-slate-400" />
                </div>
                <div v-if="item.formats?.length" class="mt-2 flex flex-wrap gap-1">
                  <span
                    v-for="format in item.formats.slice(0, 4)"
                    :key="format"
                    class="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                  >
                    {{ format }}
                  </span>
                </div>
              </RouterLink>
            </div>
            <div v-else class="text-sm text-slate-500 dark:text-slate-400">
              暂无结果
            </div>
          </section>

          <section class="card">
            <div class="mb-3 flex items-center gap-2 font-semibold">
              <div class="i-carbon-document text-amber-500" />
              来源
            </div>
            <div v-if="sources.length" class="space-y-2">
              <a
                v-for="source in sources"
                :key="`${source.source}:${source.title}`"
                :href="source.url || '#'"
                class="block rounded-lg border border-slate-200 p-3 text-sm transition-colors hover:border-amber-300 hover:bg-amber-50/60 dark:border-slate-700 dark:hover:border-amber-500 dark:hover:bg-amber-950/20"
              >
                <div class="font-medium">{{ source.title }}</div>
                <div class="mt-1 break-all text-xs text-slate-500 dark:text-slate-400">
                  {{ source.source }}
                </div>
              </a>
            </div>
            <div v-else class="text-sm text-slate-500 dark:text-slate-400">
              暂无来源
            </div>
          </section>
        </aside>
      </div>
    </section>
  </div>
</template>

<script setup>
import MarkdownViewer from "@/components/common/MarkdownViewer.vue";
import { assistantAPI } from "@/utils/api";
import { ElMessage } from "element-plus";

const question = ref("");
const sending = ref(false);
const statusLoading = ref(false);
const status = ref(null);
const lastResponse = ref(null);
const messagesEl = ref(null);
const messages = ref([
  {
    id: crypto.randomUUID(),
    role: "assistant",
    content:
      "你好，我可以根据平台资料回答使用问题，也可以帮你搜索模型和数据集。",
  },
]);

const statusLine = computed(() => {
  if (!status.value) return "大模型 · BGE RAG · 平台搜索";
  const llm = status.value.llm_configured ? status.value.llm_model : "未配置 API Key";
  return `${llm} · ${status.value.embedding_model}`;
});

const sources = computed(() => lastResponse.value?.rag?.sources || []);
const searchResults = computed(() => lastResponse.value?.search?.results || []);

function intentLabel(intent) {
  return {
    platform_qa: "平台知识问答",
    repository_search: "资源搜索",
    combined: "搜索 + RAG",
  }[intent] || intent;
}

function useExample(text) {
  question.value = text;
}

function historyForApi() {
  return messages.value
    .filter((message) => !message.loading)
    .slice(-8)
    .map((message) => ({
      role: message.role,
      content: message.content,
    }));
}

async function scrollToBottom() {
  await nextTick();
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
  }
}

async function loadStatus() {
  statusLoading.value = true;
  try {
    const { data } = await assistantAPI.status();
    status.value = data;
  } catch (err) {
    console.error("Failed to load assistant status:", err);
  } finally {
    statusLoading.value = false;
  }
}

async function send() {
  const text = question.value.trim();
  if (!text || sending.value) return;

  const userMessage = {
    id: crypto.randomUUID(),
    role: "user",
    content: text,
  };
  const assistantMessage = {
    id: crypto.randomUUID(),
    role: "assistant",
    content: "",
    loading: true,
  };

  messages.value.push(userMessage, assistantMessage);
  question.value = "";
  sending.value = true;
  await scrollToBottom();

  try {
    const requestPayload = {
      question: text,
      history: historyForApi(),
      limit: 6,
    };
    const data = await assistantAPI.chatStream(requestPayload, {
      onMeta: (meta) => {
        assistantMessage.intent = meta.intent;
        lastResponse.value = meta;
      },
      onDelta: async (chunk) => {
        assistantMessage.content += chunk;
        assistantMessage.loading = false;
        await scrollToBottom();
      },
      onDone: (result) => {
        assistantMessage.content = result.answer;
        assistantMessage.intent = result.intent;
        lastResponse.value = result;
      },
    });
    if (data) {
      assistantMessage.content = data.answer;
      assistantMessage.intent = data.intent;
      lastResponse.value = data;
    }
    assistantMessage.loading = false;
  } catch (err) {
    console.error("Assistant request failed:", err);
    assistantMessage.content =
      err.response?.data?.detail?.error || "助手暂时不可用，请稍后再试。";
    assistantMessage.loading = false;
    ElMessage.error("助手请求失败");
  } finally {
    sending.value = false;
    await scrollToBottom();
  }
}

onMounted(loadStatus);
</script>

<style scoped>
.assistant-markdown :deep(.markdown-body) {
  background: transparent;
  color: inherit;
  font-size: 0.95rem;
}

.assistant-markdown :deep(.markdown-body p:last-child) {
  margin-bottom: 0;
}

.assistant-markdown :deep(.markdown-body ul) {
  padding-left: 1.15rem;
}
</style>
