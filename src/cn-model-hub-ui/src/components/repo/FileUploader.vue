<!-- src/components/repo/FileUploader.vue -->
<template>
  <div class="file-uploader">
    <div
      class="upload-zone"
      :class="{ 'is-dragover': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      @click="$refs.fileInput.click()"
    >
      <div class="text-center py-12">
        <div
          class="i-carbon-cloud-upload text-6xl text-gray-400 dark:text-gray-500 mb-4 inline-block"
        />
        <div class="text-lg font-medium mb-2">
          拖拽文件到这里，或选择文件/文件夹上传
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          模型仓库请上传 README.md、config.json、tokenizer 文件以及
          safetensors/bin 权重文件；也可以直接选择完整模型目录。
        </div>
        <input
          ref="fileInput"
          type="file"
          multiple
          class="hidden"
          @change="handleFileSelect"
        />
        <input
          ref="folderInput"
          type="file"
          multiple
          webkitdirectory
          directory
          class="hidden"
          @change="handleFileSelect"
        />
        <div class="flex flex-col items-center justify-center gap-2 sm:flex-row">
          <el-button type="primary" @click.stop="$refs.fileInput.click()">
            <div class="i-carbon-document-add inline-block mr-1" />
            选择文件
          </el-button>
          <el-button :loading="readingFolder" @click.stop="chooseFolder">
            <div class="i-carbon-folder-add inline-block mr-1" />
            选择文件夹
          </el-button>
        </div>
      </div>
    </div>

    <div v-if="files.length > 0" class="mt-6">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-lg font-semibold">
          待上传文件（{{ files.length }}）
        </h3>
        <el-button size="small" @click="clearFiles">
          <div class="i-carbon-trash-can inline-block mr-1" />
          清空
        </el-button>
      </div>

      <div class="file-list">
        <div v-for="(fileItem, index) in files" :key="index" class="file-item">
          <div class="flex items-center gap-3 flex-1">
            <div class="i-carbon-document text-2xl text-blue-500" />
            <div class="flex-1 min-w-0">
              <div class="font-medium truncate">{{ fileItem.path }}</div>
              <div class="text-sm text-gray-500 dark:text-gray-400">
                原文件：{{ fileItem.file.name }} ·
                {{ formatFileSize(fileItem.file.size) }}
              </div>
            </div>
            <div class="flex-shrink-0" style="width: 300px">
              <el-input
                v-model="fileItem.path"
                size="small"
                placeholder="仓库内路径"
              >
                <template #prepend>/</template>
              </el-input>
            </div>
          </div>
          <el-button size="small" text @click="removeFile(index)" class="ml-2">
            <div class="i-carbon-close text-lg" />
          </el-button>
        </div>
      </div>
    </div>

    <div
      v-if="files.length > 0"
      class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700"
    >
      <h3 class="text-lg font-semibold mb-4">提交信息</h3>

      <el-form :model="commitForm" label-position="top">
        <el-form-item label="提交说明" required>
          <el-input
            v-model="commitForm.message"
            placeholder="上传模型文件"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="提交描述（可选）">
          <el-input
            v-model="commitForm.description"
            type="textarea"
            :rows="3"
            placeholder="例如：首次上传 Qwen2.5-0.5B-Instruct 模型权重和配置文件"
          />
        </el-form-item>
      </el-form>

      <div v-if="uploading" class="mb-4">
        <div
          class="text-sm font-medium mb-2"
          :class="
            isHashing
              ? 'text-blue-600 dark:text-blue-400'
              : 'text-green-600 dark:text-green-400'
          "
        >
          {{
            isHashing
              ? `正在计算 SHA256：${hashingFileName}`
              : `正在上传：${currentFileName}`
          }}
        </div>

        <el-progress
          :percentage="isHashing ? hashingProgress : uploadProgress"
          :status="uploadStatus"
          :color="isHashing ? '#409eff' : '#67c23a'"
          :show-text="true"
        />
      </div>

      <div class="flex items-center gap-3">
        <el-button
          type="primary"
          size="large"
          :disabled="!canUpload"
          :loading="uploading"
          @click="handleUpload"
        >
          <div
            v-if="!uploading"
            class="i-carbon-cloud-upload inline-block mr-1"
          />
          {{ uploading ? "正在上传..." : "上传文件" }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { ElMessage } from "element-plus";
import { repoAPI } from "@/utils/api";
import { formatFileSize } from "@/utils/lfs";

const props = defineProps({
  repoType: { type: String, required: true },
  namespace: { type: String, required: true },
  name: { type: String, required: true },
  branch: { type: String, default: "main" },
});

const emit = defineEmits(["upload-success", "upload-error"]);

// State
const files = ref([]);
const isDragging = ref(false);
const readingFolder = ref(false);
const uploading = ref(false);
const isHashing = ref(false);
const hashingProgress = ref(0);
const hashingFileName = ref("");
const uploadProgress = ref(0);
const uploadStatus = ref("");
const currentFileName = ref("");
const fileInput = ref(null);
const folderInput = ref(null);

const commitForm = ref({
  message: "上传文件",
  description: "",
});

// Computed
const canUpload = computed(() => {
  return (
    files.value.length > 0 &&
    commitForm.value.message.trim() !== "" &&
    !uploading.value &&
    files.value.every((f) => f.path.trim() !== "")
  );
});

// Methods
async function handleDrop(e) {
  isDragging.value = false;

  const droppedItems = Array.from(e.dataTransfer.items || []);
  const directoryEntries = droppedItems
    .map((item) => item.webkitGetAsEntry?.())
    .filter(Boolean);

  if (directoryEntries.length > 0) {
    readingFolder.value = true;
    try {
      const collectedFiles = [];
      for (const entry of directoryEntries) {
        await collectDroppedEntry(entry, "", collectedFiles, true);
      }
      if (collectedFiles.length > 0) {
        addFiles(collectedFiles);
        ElMessage.success(`已读取 ${collectedFiles.length} 个文件`);
        return;
      }
    } catch (err) {
      console.error("Failed to read dropped folder:", err);
      ElMessage.error("读取文件夹失败");
    } finally {
      readingFolder.value = false;
    }
  }

  const droppedFiles = Array.from(e.dataTransfer.files || []);
  addFiles(droppedFiles);
}

function handleFileSelect(e) {
  const selectedFiles = Array.from(e.target.files);
  addFiles(selectedFiles);
  // Reset input so same file can be selected again
  e.target.value = "";
}

async function chooseFolder() {
  if (window.showDirectoryPicker) {
    readingFolder.value = true;
    try {
      const directoryHandle = await window.showDirectoryPicker({
        mode: "read",
      });
      const collectedFiles = [];
      await collectDirectoryHandle(directoryHandle, "", collectedFiles);
      addFiles(collectedFiles);
      ElMessage.success(`已读取 ${collectedFiles.length} 个文件`);
    } catch (err) {
      if (err?.name !== "AbortError") {
        console.error("Failed to choose folder:", err);
        ElMessage.error("读取文件夹失败");
      }
    } finally {
      readingFolder.value = false;
    }
    return;
  }

  folderInput.value?.click();
}

function addFiles(newFiles) {
  const fileItems = newFiles
    .map((item) => {
      if (item?.file && item?.path) {
        return {
          file: item.file,
          path: normalizeRepositoryPath(item.path),
        };
      }
      return {
        file: item,
        path: normalizeSelectedPath(item),
      };
    })
    .filter((item) => item.file && item.path);
  files.value.push(...fileItems);
}

function normalizeSelectedPath(file) {
  const rawPath = (file.webkitRelativePath || file.name || "").replace(/\\/g, "/");
  const segments = rawPath.split("/").filter(Boolean);
  if (segments.length > 1) {
    return normalizeRepositoryPath(segments.slice(1).join("/"));
  }
  return normalizeRepositoryPath(segments[0] || file.name);
}

function normalizeRepositoryPath(path) {
  return String(path || "")
    .replace(/\\/g, "/")
    .split("/")
    .filter((segment) => segment && segment !== ".")
    .join("/");
}

async function collectDirectoryHandle(directoryHandle, prefix, collectedFiles) {
  for await (const [name, handle] of directoryHandle.entries()) {
    const path = prefix ? `${prefix}/${name}` : name;
    if (handle.kind === "file") {
      const file = await handle.getFile();
      collectedFiles.push({ file, path });
    } else if (handle.kind === "directory") {
      await collectDirectoryHandle(handle, path, collectedFiles);
    }
  }
}

async function collectDroppedEntry(entry, prefix, collectedFiles, isRoot = false) {
  if (entry.isFile) {
    const file = await new Promise((resolve, reject) => {
      entry.file(resolve, reject);
    });
    const path = prefix ? `${prefix}/${entry.name}` : entry.name;
    collectedFiles.push({ file, path });
    return;
  }

  if (!entry.isDirectory) return;

  const reader = entry.createReader();
  const childEntries = await readAllDirectoryEntries(reader);
  const nextPrefix = isRoot ? prefix : prefix ? `${prefix}/${entry.name}` : entry.name;
  for (const childEntry of childEntries) {
    await collectDroppedEntry(childEntry, nextPrefix, collectedFiles, false);
  }
}

async function readAllDirectoryEntries(reader) {
  const entries = [];
  while (true) {
    const batch = await new Promise((resolve, reject) => {
      reader.readEntries(resolve, reject);
    });
    if (!batch.length) break;
    entries.push(...batch);
  }
  return entries;
}

function removeFile(index) {
  files.value.splice(index, 1);
}

function clearFiles() {
  files.value = [];
  isHashing.value = false;
  hashingProgress.value = 0;
  hashingFileName.value = "";
  uploadProgress.value = 0;
  uploadStatus.value = "";
  currentFileName.value = "";
}

async function handleUpload() {
  if (!canUpload.value) return;

  uploading.value = true;
  isHashing.value = true;
  hashingProgress.value = 0;
  uploadProgress.value = 0;
  uploadStatus.value = "";

  try {
    await repoAPI.uploadFiles(
      props.repoType,
      props.namespace,
      props.name,
      props.branch,
      {
        files: files.value,
        message: commitForm.value.message,
        description: commitForm.value.description,
      },
      {
        onHashProgress: (fileName, progress) => {
          isHashing.value = true;
          hashingFileName.value = fileName;
          hashingProgress.value = Math.round(progress * 100);
        },
        onUploadProgress: (fileName, progress) => {
          isHashing.value = false;
          currentFileName.value = fileName;
          uploadProgress.value = Math.round(progress * 100);
        },
      },
    );

    uploadStatus.value = "success";
    ElMessage.success("文件上传成功");
    emit("upload-success");

    setTimeout(() => {
      clearFiles();
      commitForm.value.message = "上传文件";
      commitForm.value.description = "";
    }, 1000);
  } catch (err) {
    uploadStatus.value = "exception";
    const detail = err.response?.data?.detail;
    const errorMsg =
      (typeof detail === "string" ? detail : detail?.message || detail?.error) ||
      "文件上传失败";
    ElMessage.error(errorMsg);
    emit("upload-error", err);
    console.error("Upload error:", err);
  } finally {
    uploading.value = false;
  }
}

// Expose methods
defineExpose({
  clearFiles,
  handleUpload,
});
</script>

<style scoped>
.upload-zone {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  background-color: #f9fafb;
  transition: all 0.3s;
  cursor: pointer;
}

.dark .upload-zone {
  border-color: #374151;
  background-color: #1f2937;
}

.upload-zone:hover {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.dark .upload-zone:hover {
  border-color: #60a5fa;
  background-color: #1e3a5f;
}

.upload-zone.is-dragover {
  border-color: #3b82f6;
  background-color: #dbeafe;
}

.dark .upload-zone.is-dragover {
  border-color: #60a5fa;
  background-color: #1e40af;
}

.file-list {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.dark .file-list {
  border-color: #374151;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  background-color: white;
  transition: background-color 0.2s;
}

.dark .file-item {
  border-bottom-color: #374151;
  background-color: #1f2937;
}

.file-item:last-child {
  border-bottom: none;
}

.file-item:hover {
  background-color: #f9fafb;
}

.dark .file-item:hover {
  background-color: #111827;
}
</style>
