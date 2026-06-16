<script setup>
import { onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import MarkdownPage from "@/components/common/MarkdownPage.vue";

const route = useRoute();
const content = ref("");
const loading = ref(true);
const directoryDocs = ref([]);
const isDirectory = ref(false);

function parseFrontmatter(markdown) {
  const match = markdown.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (!match) {
    return {};
  }
  return Object.fromEntries(
    match[1]
      .split("\n")
      .map((line) => line.split(":"))
      .filter((parts) => parts.length >= 2)
      .map(([key, ...value]) => [key.trim(), value.join(":").trim()]),
  );
}

function fallbackTitle(filename) {
  return filename.replace(".md", "").replace(/-/g, " ");
}

async function loadDoc() {
  loading.value = true;
  content.value = "";
  directoryDocs.value = [];
  isDirectory.value = false;

  const docPath = route.path.split("/").filter(Boolean).slice(1).join("/");
  try {
    const fileResponse = await fetch(`/documentation/${docPath}.md`);
    if (fileResponse.ok) {
      const text = await fileResponse.text();
      if (!text.trim().startsWith("<!DOCTYPE") && !text.trim().startsWith("<html")) {
        content.value = text;
        loading.value = false;
        return;
      }
    }

    const manifestResponse = await fetch(`/documentation/${docPath}/.manifest.json`);
    if (manifestResponse.ok) {
      const manifestText = await manifestResponse.text();
      const files = JSON.parse(manifestText);
      const docs = await Promise.all(
        files.map(async (filename) => {
          const response = await fetch(`/documentation/${docPath}/${filename}`);
          if (!response.ok) {
            return null;
          }
          const markdown = await response.text();
          const meta = parseFrontmatter(markdown);
          const heading = markdown.match(/^#\s+(.+)$/m);
          return {
            title: meta.title || heading?.[1] || fallbackTitle(filename),
            description: meta.description || "",
            path: `/docs/${docPath}/${filename.replace(".md", "")}`,
          };
        }),
      );
      directoryDocs.value = docs.filter(Boolean);
      isDirectory.value = true;
      loading.value = false;
      return;
    }

    content.value = "# 文档不存在\n\n[返回知识库](/docs)";
  } catch (error) {
    content.value = `# 文档加载失败\n\n${error.message}\n\n[返回知识库](/docs)`;
  } finally {
    loading.value = false;
  }
}

onMounted(loadDoc);
watch(() => route.path, loadDoc);
</script>

<template>
  <div v-if="loading" class="container-main py-12 text-center text-slate-500">
    <div class="i-carbon-circle-dash mx-auto mb-3 animate-spin text-4xl" />
    正在加载知识库...
  </div>

  <div v-else-if="isDirectory" class="container-main py-12">
    <div class="mx-auto max-w-5xl">
      <h1 class="text-4xl font-bold">平台知识库</h1>
      <p class="mt-3 text-slate-600 dark:text-slate-400">
        智能助手只索引这里的中文 Markdown 文档。
      </p>

      <div class="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
        <RouterLink
          v-for="doc in directoryDocs"
          :key="doc.path"
          :to="doc.path"
          class="card p-5 hover:shadow-lg"
        >
          <h2 class="text-lg font-semibold">{{ doc.title }}</h2>
          <p v-if="doc.description" class="mt-2 text-sm text-slate-500">
            {{ doc.description }}
          </p>
        </RouterLink>
      </div>

      <RouterLink to="/docs" class="mt-8 inline-flex text-blue-600 hover:underline">
        返回知识库首页
      </RouterLink>
    </div>
  </div>

  <MarkdownPage v-else :content="content" />
</template>
