<template>
  <div class="container-main">
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
          {{ repoTypeLabel }}
        </RouterLink>
      </el-breadcrumb-item>
      <el-breadcrumb-item>
        <RouterLink
          :to="namespaceLink"
          class="text-blue-600 dark:text-blue-400 hover:underline"
        >
          {{ namespace }}
        </RouterLink>
      </el-breadcrumb-item>
      <el-breadcrumb-item>
        <RouterLink
          :to="`/${repoType}s/${namespace}/${name}`"
          class="text-blue-600 dark:text-blue-400 hover:underline"
        >
          {{ name }}
        </RouterLink>
      </el-breadcrumb-item>
    </el-breadcrumb>

    <div v-if="loading" class="py-20 text-center">
      <el-icon class="is-loading" :size="40">
        <div class="i-carbon-loading" />
      </el-icon>
    </div>

    <div v-else-if="error" class="py-20 text-center">
      <div class="i-carbon-warning mb-4 text-6xl text-red-500" />
      <h2 class="mb-2 text-2xl font-bold">未找到仓库</h2>
      <p class="mb-4 text-gray-600">{{ error }}</p>
      <el-button @click="$router.back()">返回</el-button>
    </div>

    <div
      v-else
      :class="
        activeTab === 'viewer'
          ? ''
          : 'grid grid-cols-1 gap-6 lg:grid-cols-[1fr_300px]'
      "
    >
      <main class="min-w-0">
        <div v-if="activeTab !== 'viewer'" class="card mb-6">
          <div
            class="mb-4 flex flex-col items-start justify-between gap-4 sm:flex-row"
          >
            <div class="flex items-start gap-3">
              <div
                :class="getIconClass(repoType)"
                class="flex-shrink-0 text-3xl sm:text-4xl"
              />
              <div class="min-w-0">
                <h1 class="break-words text-xl font-bold sm:text-2xl lg:text-3xl">
                  {{ repoDisplayTitle }}
                </h1>
                <div class="mt-1 flex items-center gap-2">
                  <RouterLink
                    :to="namespaceLink"
                    class="text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {{ namespace }}
                  </RouterLink>
                  <span class="text-gray-400 dark:text-gray-500">/</span>
                  <span class="text-gray-700 dark:text-gray-300">{{ name }}</span>
                  <button
                    @click="copyRepoId"
                    class="ml-1 rounded p-1 transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
                    title="复制仓库 ID"
                  >
                    <div
                      class="i-carbon-copy text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    />
                  </button>
                </div>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <el-tag v-if="repoInfo?.private" type="warning">
                <div class="i-carbon-locked mr-1 inline-block" />
                私有
              </el-tag>
              <el-tag v-else type="success">
                <div class="i-carbon-unlocked mr-1 inline-block" />
                公开
              </el-tag>
              <el-tag v-if="isExternalRepo" type="info">
                <div class="i-carbon-cloud mr-1 inline-block" />
                {{ repoInfo._source }}
              </el-tag>
              <el-button
                v-if="isExternalRepo && repoInfo._source_url"
                size="small"
                type="primary"
                plain
                @click="openExternalRepo"
              >
                <div class="i-carbon-launch mr-1 inline-block" />
                在 {{ repoInfo._source }} 查看
              </el-button>
            </div>
          </div>

          <div
            class="flex flex-wrap items-center gap-3 text-xs text-gray-600 dark:text-gray-400 sm:gap-6 sm:text-sm"
          >
            <div class="flex items-center gap-1">
              <div class="i-carbon-download" />
              <span>{{ repoInfo?.downloads || 0 }} 次下载</span>
            </div>
            <button
              v-if="authStore.isAuthenticated"
              @click="toggleLike"
              :class="[
                'flex items-center gap-1 transition-all hover:scale-105',
                isLiked
                  ? 'text-red-500 dark:text-red-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-red-500 dark:hover:text-red-400',
              ]"
              :disabled="likingInProgress"
            >
              <div
                :class="isLiked ? 'i-carbon-favorite-filled' : 'i-carbon-favorite'"
              />
              <span>{{ likesCount }}</span>
            </button>
            <div v-else class="flex items-center gap-1">
              <div class="i-carbon-favorite" />
              <span>{{ likesCount }}</span>
            </div>
            <div class="flex items-center gap-1">
              <div class="i-carbon-calendar" />
              <span>更新于 {{ formatDate(repoInfo?.lastModified) }}</span>
            </div>
          </div>

          <div class="mt-4 flex flex-col gap-1 sm:flex-row">
            <el-button
              v-if="isOwner && !isExternalRepo"
              type="primary"
              @click="navigateToUpload"
              size="small"
              class="m-0 w-full sm:m-1 sm:w-auto"
            >
              <div class="i-carbon-cloud-upload mr-1 inline-block" />
              上传文件
            </el-button>
            <el-button
              @click="downloadRepo"
              size="small"
              class="m-0 w-full sm:m-1 sm:w-auto"
              plain
            >
              <div class="i-carbon-document-download mr-1 inline-block" />
              下载
            </el-button>
            <el-button
              v-if="isOwner"
              @click="navigateToSettings"
              size="small"
              class="m-0 w-full sm:m-1 sm:w-auto"
              plain
            >
              <div class="i-carbon-settings mr-1 inline-block" />
              设置
            </el-button>
          </div>
        </div>

        <MetadataHeader
          v-if="hasMetadataHeader && activeTab !== 'viewer'"
          :metadata="readmeMetadata"
          :repo-type="repoType"
          @navigate-to-metadata="navigateToTab('metadata')"
        />

        <div class="mb-6 -mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <div class="flex min-w-max gap-1 border-b border-gray-200 dark:border-gray-700 sm:min-w-0">
            <button
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'card'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
              ]"
              @click="navigateToTab('card')"
            >
              {{
                repoType === 'model'
                  ? '模型卡片'
                  : repoType === 'dataset'
                    ? '数据集卡片'
                    : '说明'
              }}
            </button>
            <button
              v-if="repoType === 'model' || repoType === 'space'"
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'runtime'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
              ]"
              @click="navigateToTab('runtime')"
            >
              <div class="i-carbon-application-web mr-1 inline-block" />
              运行
            </button>
            <button
              v-if="repoType === 'model'"
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'evaluations'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
                isExternalRepo ? 'cursor-not-allowed opacity-50' : '',
              ]"
              @click="!isExternalRepo && navigateToTab('evaluations')"
              :disabled="isExternalRepo"
              :title="
                isExternalRepo
                  ? `外部仓库 ${externalSourceName} 暂不支持本地评测`
                  : ''
              "
            >
              <div class="i-carbon-trophy mr-1 inline-block" />
              评测
            </button>
            <button
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'files'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
              ]"
              @click="navigateToTab('files')"
            >
              文件
            </button>
            <button
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'commits'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
                isExternalRepo ? 'cursor-not-allowed opacity-50' : '',
              ]"
              @click="!isExternalRepo && navigateToTab('commits')"
              :disabled="isExternalRepo"
              :title="
                isExternalRepo
                  ? `外部仓库 ${externalSourceName} 暂不支持提交记录`
                  : ''
              "
            >
              提交记录
            </button>
            <button
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'discussions'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
                isExternalRepo ? 'cursor-not-allowed opacity-50' : '',
              ]"
              @click="!isExternalRepo && navigateToTab('discussions')"
              :disabled="isExternalRepo"
              :title="
                isExternalRepo
                  ? `外部仓库 ${externalSourceName} 暂不支持本地讨论`
                  : ''
              "
            >
              讨论
            </button>
            <button
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'metadata'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
              ]"
              @click="navigateToTab('metadata')"
            >
              元数据
            </button>
            <button
              v-if="repoType === 'dataset'"
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'viewer'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
              ]"
              @click="navigateToTab('viewer')"
            >
              <div class="i-carbon-data-table mr-1 inline-block" />
              预览
            </button>
          </div>
        </div>

        <div v-if="activeTab === 'card'" class="card overflow-hidden">
          <div class="max-w-full overflow-x-auto">
            <div v-if="readmeLoading" class="py-12 text-center">
              <el-icon class="is-loading" :size="40">
                <div class="i-carbon-loading" />
              </el-icon>
              <p class="mt-4 text-gray-500 dark:text-gray-400">
                正在加载 README...
              </p>
            </div>
            <div v-else-if="readmeContent">
              <MarkdownViewer
                :content="readmeContent"
                :repo-type="repoType"
                :namespace="namespace"
                :name="name"
                :branch="currentBranch"
              />
            </div>
            <ErrorState
              v-else-if="readmeErrorClassification"
              :classification="readmeErrorClassification"
              mode="inline-panel"
              :retry="loadReadme"
            />
            <div v-else class="py-12 text-center text-gray-500 dark:text-gray-400">
              <div class="i-carbon-document-blank mb-4 inline-block text-6xl" />
              <p>未找到 README.md</p>
              <div
                v-if="isOwner"
                class="mt-4 flex flex-col items-center justify-center gap-2 sm:flex-row"
              >
                <el-button type="primary" @click="navigateToUpload">
                  <div class="i-carbon-cloud-upload mr-1 inline-block" />
                  上传仓库文件
                </el-button>
                <el-button @click="createReadme">
                  创建 README.md
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'metadata'">
          <DetailedMetadataPanel
            v-if="hasDetailedMetadata"
            :metadata="readmeMetadata"
            :repo-type="repoType"
          />
          <div v-else class="card py-12 text-center text-gray-500 dark:text-gray-400">
            <div class="i-carbon-information mb-4 inline-block text-6xl" />
            <p>README.md 中未找到元数据</p>
            <p class="mt-2 text-sm">
              在 README.md 中加入 YAML frontmatter 即可显示元数据
            </p>
          </div>
        </div>

        <div v-if="activeTab === 'viewer' && repoType === 'dataset'">
          <DatasetViewerTab
            :repo-type="repoType"
            :namespace="namespace"
            :name="name"
            :branch="currentBranch"
            :files="fileTree"
          />
        </div>

        <div
          v-if="
            activeTab === 'runtime' &&
            (repoType === 'model' || repoType === 'space')
          "
        >
          <SpaceRuntimePanel
            :repo-type="repoType"
            :namespace="namespace"
            :name="name"
            :branch="currentBranch"
            :is-owner="isOwner"
          />
        </div>

        <div v-if="activeTab === 'evaluations' && repoType === 'model'">
          <QuickEvaluationPanel
            :repo-type="repoType"
            :namespace="namespace"
            :name="name"
            :branch="currentBranch"
            :is-owner="isOwner"
          />
        </div>

        <div v-if="activeTab === 'files'" class="card">
          <div
            class="mb-4 flex flex-col items-stretch justify-between gap-3 sm:flex-row sm:items-center"
          >
            <div class="flex min-w-0 items-center gap-2">
              <el-select
                v-model="currentBranch"
                size="small"
                class="min-w-28 w-full sm:w-37 sm:min-w-37 sm:flex-none"
                @change="handleBranchChange"
              >
                <el-option label="main" value="main" />
              </el-select>
              <span
                class="whitespace-nowrap text-sm text-gray-600 dark:text-gray-400"
                data-testid="file-list-count"
              >
                {{ fileTree.length }}
                {{ fileTree.length === 1 ? "个文件" : "个文件" }}<template v-if="fileListHasMore"> 已加载</template>
              </span>
            </div>

            <div class="flex items-stretch gap-2 sm:flex-row sm:items-center">
              <el-button
                v-if="isOwner"
                size="small"
                type="primary"
                @click="navigateToUpload"
                class="w-full sm:w-auto"
              >
                <div class="i-carbon-cloud-upload mr-1 inline-block" />
                上传文件
              </el-button>
              <el-input
                v-model="fileSearchQuery"
                placeholder="按名称前缀筛选..."
                size="small"
                class="w-full sm:w-50"
                clearable
                data-testid="file-list-name-prefix"
              >
                <template #prefix>
                  <div class="i-carbon-search" />
                </template>
              </el-input>
            </div>
          </div>

          <div v-if="currentPath" class="mb-3">
            <div class="flex items-center justify-between">
              <el-breadcrumb
                separator="/"
                class="text-sm text-gray-700 dark:text-gray-300"
              >
                <el-breadcrumb-item>
                  <RouterLink
                    :to="`/${repoType}s/${namespace}/${name}/tree/${currentBranch}`"
                    class="text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    根目录
                  </RouterLink>
                </el-breadcrumb-item>
                <el-breadcrumb-item
                  v-for="(segment, idx) in pathSegments"
                  :key="idx"
                >
                  <RouterLink
                    :to="`/${repoType}s/${namespace}/${name}/tree/${currentBranch}/${pathSegments.slice(0, idx + 1).join('/')}`"
                    class="text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {{ segment }}
                  </RouterLink>
                </el-breadcrumb-item>
              </el-breadcrumb>
              <el-button
                v-if="isOwner"
                @click="confirmDeleteFolder"
                type="danger"
                size="small"
                :loading="deletingFolder"
              >
                <div class="i-carbon-trash-can mr-1 inline-block" />
                删除文件夹
              </el-button>
            </div>
          </div>

          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            <div v-if="filesLoading" class="py-12 text-center">
              <el-icon class="is-loading" :size="40">
                <div class="i-carbon-loading" />
              </el-icon>
              <p class="mt-4 text-gray-500 dark:text-gray-400">正在加载文件...</p>
            </div>
            <ErrorState
              v-else-if="treeErrorClassification"
              :classification="treeErrorClassification"
              mode="inline-panel"
              :retry="loadFileTree"
            />
            <template v-else>
              <div
                class="hidden gap-3 border-b border-gray-200 py-2 px-2 text-sm font-medium text-gray-600 dark:border-gray-700 dark:text-gray-400 md:grid md:grid-cols-[auto_minmax(0,1.4fr)_minmax(0,2fr)_120px_110px]"
              >
                <div></div>
                <div>名称</div>
                <div>最近提交</div>
                <div class="text-right">更新时间</div>
                <div class="text-right">大小</div>
              </div>

              <div
                v-for="file in fileTree"
                :key="file.path"
                class="relative grid cursor-pointer grid-cols-[auto_1fr] items-center gap-3 px-2 py-3 transition-colors hover:bg-gray-50 dark:hover:bg-gray-700 md:grid-cols-[auto_minmax(0,1.4fr)_minmax(0,2fr)_120px_110px]"
              >
                <RouterLink
                  :to="getEntryHref(file)"
                  :aria-label="`打开 ${getFileName(file.path)}`"
                  class="absolute inset-0 z-10"
                  data-testid="filelist-row-link"
                />
                <div
                  :class="
                    file.type === 'directory'
                      ? 'i-carbon-folder text-blue-500'
                      : 'i-carbon-document text-gray-500 dark:text-gray-400'
                  "
                  class="flex-shrink-0 text-xl"
                />
                <div class="min-w-0">
                  <div class="flex items-center gap-2 font-medium truncate">
                    <span class="truncate">{{ getFileName(file.path) }}</span>
                    <button
                      v-if="canPreviewFileRow(file)"
                      type="button"
                      class="relative z-20 flex-shrink-0 text-gray-400 transition-colors hover:text-blue-500 dark:hover:text-blue-400"
                      :title="previewIconTitle(file)"
                      :aria-label="`预览 ${getFileName(file.path)} 的元数据`"
                      @click.stop="openFilePreview(file)"
                    >
                      <div :class="previewIconClass(file)" class="text-base" />
                    </button>
                  </div>
                  <div class="mt-1 truncate text-sm text-gray-500 dark:text-gray-400 md:hidden">
                    <RouterLink
                      v-if="file.lastCommit"
                      :to="getCommitPath(file.lastCommit.id)"
                      class="relative z-20 text-gray-700 underline underline-offset-2 decoration-gray-400 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100"
                      :title="file.lastCommit.title"
                      @click.stop
                    >
                      {{ getEntryCommitTitle(file) }}
                    </RouterLink>
                    <span v-else>{{ getEntryCommitTitle(file) }}</span>
                  </div>
                  <div class="mt-1 text-xs text-gray-400 dark:text-gray-500 md:hidden">
                    {{ getEntryUpdatedAt(file) }}
                    <span v-if="formatEntrySize(file) !== '-'">
                      · {{ formatEntrySize(file) }}
                    </span>
                  </div>
                </div>
                <div class="hidden min-w-0 truncate text-sm text-gray-500 dark:text-gray-400 md:block">
                  <RouterLink
                    v-if="file.lastCommit"
                    :to="getCommitPath(file.lastCommit.id)"
                    class="relative z-20 text-gray-700 underline underline-offset-2 decoration-gray-400 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100"
                    :title="file.lastCommit.title"
                    @click.stop
                  >
                    {{ getEntryCommitTitle(file) }}
                  </RouterLink>
                  <span v-else>{{ getEntryCommitTitle(file) }}</span>
                </div>
                <div class="hidden text-right text-sm text-gray-500 dark:text-gray-400 md:block">
                  {{ getEntryUpdatedAt(file) }}
                </div>
                <div class="hidden text-right text-sm text-gray-500 dark:text-gray-400 md:block">
                  {{ formatEntrySize(file) }}
                </div>
              </div>

              <div
                v-if="fileTree.length === 0"
                class="py-12 text-center text-gray-500 dark:text-gray-400"
              >
                <div class="i-carbon-document-blank mb-4 inline-block text-6xl" />
                <p v-if="fileSearchQuery">当前目录没有以“{{ fileSearchQuery }}”开头的文件</p>
                <p v-else>未找到文件</p>
                <el-button
                  v-if="isOwner && !fileSearchQuery"
                  class="mt-4"
                  type="primary"
                  @click="navigateToUpload"
                >
                  <div class="i-carbon-cloud-upload mr-1 inline-block" />
                  上传文件
                </el-button>
              </div>
            </template>
          </div>

          <div v-if="!filesLoading && fileListHasMore" class="pt-4 text-center">
            <el-button
              :loading="fileListLoadingMore"
              :disabled="fileListLoadingMore"
              plain
              data-testid="file-list-load-more"
              @click="loadMoreFileTree"
            >
              加载更多文件
            </el-button>
          </div>
        </div>

        <div v-if="activeTab === 'commits'">
          <div v-if="isExternalRepo" class="card py-12 text-center">
            <div class="i-carbon-warning mb-4 inline-block text-6xl text-yellow-500 dark:text-yellow-400" />
            <h3 class="mb-2 text-xl font-semibold text-gray-900 dark:text-white">
              当前不支持查看提交记录
            </h3>
            <p class="mb-4 text-gray-600 dark:text-gray-400">
              该仓库来自 {{ externalSourceName }}，外部仓库暂不提供提交历史。
            </p>
            <p class="text-sm text-gray-500 dark:text-gray-500">
              请前往源仓库查看提交记录。
            </p>
          </div>

          <div v-else class="card">
            <h2 class="mb-4 text-xl font-semibold">提交历史</h2>
            <div v-if="commitsLoading && commits.length === 0" class="py-12 text-center">
              <el-icon class="is-loading" :size="40">
                <div class="i-carbon-renew" />
              </el-icon>
              <p class="mt-4 text-gray-500 dark:text-gray-400">正在加载提交...</p>
            </div>

            <div v-else-if="commits.length > 0" class="space-y-3">
              <div
                v-for="commit in commits"
                :key="commit.id"
                class="cursor-pointer rounded-lg border border-gray-200 p-4 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/50"
                @click="viewCommit(commit.id)"
              >
                <div class="flex items-start gap-3">
                  <div class="i-carbon-commit mt-1 flex-shrink-0 text-2xl text-blue-500" />
                  <div class="min-w-0 flex-1">
                    <div class="mb-1 text-sm font-medium">
                      <RouterLink
                        :to="getCommitPath(commit.id)"
                        class="block text-gray-900 transition-colors hover:text-blue-600 dark:text-gray-100 dark:hover:text-blue-400"
                        @click.stop
                      >
                        {{ commit.title }}
                      </RouterLink>
                    </div>
                    <div class="flex items-center gap-3 text-xs text-gray-600 dark:text-gray-400">
                      <div class="flex items-center gap-1">
                        <div class="i-carbon-user-avatar" />
                        <RouterLink
                          :to="`/${commit.author}`"
                          class="text-blue-600 hover:underline dark:text-blue-400"
                          @click.stop
                        >
                          {{ commit.author }}
                        </RouterLink>
                      </div>
                      <div class="flex items-center gap-1">
                        <div class="i-carbon-calendar" />
                        <span>{{ formatCommitDate(commit.date) }}</span>
                      </div>
                      <div class="font-mono text-xs">{{ commit.id.slice(0, 7) }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="commitsHasMore" class="pt-4 text-center">
                <el-button @click="loadMoreCommits" :loading="commitsLoading" plain>
                  加载更多提交
                </el-button>
              </div>
            </div>

            <div v-else class="py-12 text-center text-gray-500 dark:text-gray-400">
              <div class="i-carbon-branch mb-4 inline-block text-6xl" />
              <p>暂无提交记录</p>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'discussions'">
          <div v-if="isExternalRepo" class="card py-12 text-center">
            <div class="i-carbon-warning mb-4 inline-block text-6xl text-yellow-500 dark:text-yellow-400" />
            <h3 class="mb-2 text-xl font-semibold text-gray-900 dark:text-white">
              当前不支持本地讨论
            </h3>
            <p class="text-gray-600 dark:text-gray-400">
              该仓库来自 {{ externalSourceName }}，请前往源仓库参与交流。
            </p>
          </div>

          <div v-else class="space-y-4">
            <div class="card">
              <div
                class="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center"
              >
                <div>
                  <h2 class="text-xl font-semibold">讨论区</h2>
                  <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    交流模型使用、数据质量、评测结果和改进建议。
                  </p>
                </div>
                <el-tag type="info" effect="plain">
                  {{ discussions.length }} 个话题
                </el-tag>
              </div>

              <div
                v-if="authStore.isAuthenticated"
                class="mb-6 rounded-lg border border-gray-200 p-4 dark:border-gray-700"
              >
                <div class="mb-3 font-medium">发起讨论</div>
                <el-input
                  v-model="newDiscussion.title"
                  maxlength="160"
                  show-word-limit
                  placeholder="例如：这个模型在中文问答任务上的表现如何？"
                  class="mb-3"
                />
                <el-input
                  v-model="newDiscussion.body"
                  type="textarea"
                  :rows="4"
                  maxlength="20000"
                  show-word-limit
                  placeholder="写下背景、复现步骤、评测指标或你的建议..."
                  class="mb-3"
                />
                <div class="flex justify-end">
                  <el-button
                    type="primary"
                    :loading="creatingDiscussion"
                    @click="submitDiscussion"
                  >
                    发布讨论
                  </el-button>
                </div>
              </div>

              <div
                v-else
                class="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-100"
              >
                登录后可以发起讨论和回复。
              </div>

              <div v-if="discussionsLoading" class="py-12 text-center">
                <el-icon class="is-loading" :size="36">
                  <div class="i-carbon-renew" />
                </el-icon>
                <p class="mt-3 text-gray-500 dark:text-gray-400">
                  正在加载讨论...
                </p>
              </div>

              <div v-else-if="discussions.length > 0" class="space-y-3">
                <button
                  v-for="discussion in discussions"
                  :key="discussion.id"
                  type="button"
                  :class="[
                    'w-full rounded-lg border p-4 text-left transition-colors',
                    selectedDiscussionId === discussion.id
                      ? 'border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-950/30'
                      : 'border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800/50',
                  ]"
                  @click="selectDiscussion(discussion.id)"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <div class="truncate font-medium text-gray-900 dark:text-gray-100">
                        {{ discussion.title }}
                      </div>
                      <div class="mt-1 flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                        <span>{{ discussion.author?.name || discussion.author?.username }}</span>
                        <span>{{ formatDate(discussion.updatedAt) }}</span>
                      </div>
                    </div>
                    <div class="flex shrink-0 items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
                      <div class="i-carbon-chat" />
                      {{ discussion.commentCount || 0 }}
                    </div>
                  </div>
                </button>
              </div>

              <div v-else class="py-12 text-center text-gray-500 dark:text-gray-400">
                <div class="i-carbon-chat mb-4 inline-block text-6xl" />
                <p>暂无讨论</p>
              </div>
            </div>

            <div v-if="selectedDiscussionId" class="card">
              <div v-if="discussionDetailsLoading" class="py-12 text-center">
                <el-icon class="is-loading" :size="36">
                  <div class="i-carbon-renew" />
                </el-icon>
              </div>

              <template v-else-if="selectedDiscussion">
                <div class="mb-5 flex items-start justify-between gap-4">
                  <div class="min-w-0">
                    <h3 class="break-words text-xl font-semibold">
                      {{ selectedDiscussion.title }}
                    </h3>
                    <div class="mt-2 flex flex-wrap items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                      <span>{{ selectedDiscussion.author?.name || selectedDiscussion.author?.username }}</span>
                      <span>发布于 {{ formatDate(selectedDiscussion.createdAt) }}</span>
                    </div>
                  </div>
                  <el-button
                    v-if="canDeleteDiscussion(selectedDiscussion)"
                    size="small"
                    type="danger"
                    plain
                    :loading="deletingDiscussionId === selectedDiscussion.id"
                    @click="confirmDeleteDiscussion(selectedDiscussion)"
                  >
                    删除
                  </el-button>
                </div>

                <div class="mb-6 whitespace-pre-wrap break-words rounded-lg bg-gray-50 p-4 text-sm leading-6 text-gray-800 dark:bg-gray-900 dark:text-gray-100">
                  {{ selectedDiscussion.body }}
                </div>

                <div class="mb-3 flex items-center justify-between">
                  <h4 class="font-semibold">回复</h4>
                  <span class="text-sm text-gray-500 dark:text-gray-400">
                    {{ discussionComments.length }} 条
                  </span>
                </div>

                <div v-if="discussionComments.length > 0" class="space-y-3">
                  <div
                    v-for="comment in discussionComments"
                    :key="comment.id"
                    class="rounded-lg border border-gray-200 p-4 dark:border-gray-700"
                  >
                    <div class="mb-2 flex items-start justify-between gap-3">
                      <div class="flex flex-wrap items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                        <span class="font-medium text-gray-800 dark:text-gray-100">
                          {{ comment.author?.name || comment.author?.username }}
                        </span>
                        <span>{{ formatDate(comment.createdAt) }}</span>
                      </div>
                      <el-button
                        v-if="canDeleteComment(comment)"
                        size="small"
                        type="danger"
                        text
                        :loading="deletingCommentId === comment.id"
                        @click="confirmDeleteComment(comment)"
                      >
                        删除
                      </el-button>
                    </div>
                    <div class="whitespace-pre-wrap break-words text-sm leading-6">
                      {{ comment.body }}
                    </div>
                  </div>
                </div>

                <div v-else class="rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                  还没有回复，来补充第一条观点。
                </div>

                <div v-if="authStore.isAuthenticated" class="mt-5">
                  <el-input
                    v-model="newCommentBody"
                    type="textarea"
                    :rows="4"
                    maxlength="12000"
                    show-word-limit
                    placeholder="写下你的回复..."
                  />
                  <div class="mt-3 flex justify-end">
                    <el-button
                      type="primary"
                      :loading="creatingComment"
                      @click="submitComment"
                    >
                      发布回复
                    </el-button>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </main>

      <aside v-if="activeTab !== 'viewer'" class="space-y-4 lg:sticky lg:top-20 lg:self-start">
        <SidebarRelationshipsCard
          :namespace="namespace"
          :namespace-link="namespaceLink"
          :metadata="readmeMetadata"
          :repo-type="repoType"
        />

        <div class="card">
          <h3 class="mb-3 font-semibold">信息</h3>
          <div class="space-y-2 text-sm">
            <div>
              <span class="text-gray-600 dark:text-gray-400">类型：</span>
              <span class="ml-2 font-medium">{{ repoTypeLabel }}</span>
            </div>
            <div>
              <span class="text-gray-600 dark:text-gray-400">创建于：</span>
              <span class="ml-2">{{ formatDate(repoInfo?.createdAt) }}</span>
            </div>
            <div v-if="repoInfo?.lastModified">
              <span class="text-gray-600 dark:text-gray-400">更新于：</span>
              <span class="ml-2">{{ formatDate(repoInfo?.lastModified) }}</span>
            </div>
            <div v-if="repoInfo?.sha">
              <span class="text-gray-600 dark:text-gray-400">提交：</span>
              <span class="ml-2 font-mono text-xs">{{ repoInfo.sha.slice(0, 7) }}</span>
            </div>
          </div>
        </div>

        <div v-if="repoInfo?.storage" class="card">
          <h3 class="mb-3 font-semibold">存储</h3>
          <div class="space-y-3 text-sm">
            <div>
              <div class="mb-1 flex items-center justify-between">
                <span class="text-gray-600 dark:text-gray-400">使用量：</span>
                <span class="font-medium">{{ formatSize(repoInfo.storage.used_bytes) }}</span>
              </div>
              <div
                v-if="repoInfo.storage.effective_quota_bytes"
                class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400"
              >
                <span>上限：</span>
                <span>{{ formatSize(repoInfo.storage.effective_quota_bytes) }}</span>
              </div>
              <div
                v-if="
                  repoInfo.storage.percentage_used !== null &&
                  repoInfo.storage.percentage_used !== undefined
                "
                class="mt-2"
              >
                <el-progress
                  :percentage="
                    Math.min(
                      100,
                      Math.round(repoInfo.storage.percentage_used * 100) / 100,
                    )
                  "
                  :color="getProgressColor(repoInfo.storage.percentage_used)"
                  :stroke-width="6"
                  :format="(percentage) => `${percentage.toFixed(2)}%`"
                />
              </div>
              <div
                v-if="repoInfo.storage.is_inheriting"
                class="mt-2 text-xs text-gray-500 dark:text-gray-400"
              >
                <div class="i-carbon-information mr-1 inline-block" />
                继承自 {{ namespace }} 的配额
              </div>
            </div>
          </div>
        </div>
        <RepoMlflowPanel
          v-if="repoInfo?.mlflow && !isExternalRepo"
          :repo-type="repoType"
          :namespace="namespace"
          :name="name"
          :is-owner="isOwner"
          :initial-binding="repoInfo.mlflow"
          @binding-updated="handleMlflowBindingUpdated"
        />
      </aside>
    </div>

    <FilePreviewDialog
      v-if="previewTarget"
      v-model:visible="previewDialogVisible"
      :kind="previewTarget.kind"
      :resolve-url="previewTarget.resolveUrl"
      :filename="previewTarget.filename"
    />

    <TarBrowserDialog
      v-if="tarBrowserTarget"
      v-model:visible="tarBrowserDialogVisible"
      :tar-url="tarBrowserTarget.tarUrl"
      :index-url="tarBrowserTarget.indexUrl"
      :filename="tarBrowserTarget.filename"
      :tar-tree-entry="tarBrowserTarget.tarTreeEntry"
    />
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from "element-plus";
import axios from "axios";
import {
  formatRelativeTime,
  formatUnixRelativeTime,
} from "@/utils/datetime";

import { useAuthStore } from "@/stores/auth";
import { copyToClipboard } from "@/utils/clipboard";
import { parseYAMLFrontmatter, normalizeMetadata } from "@/utils/yaml-parser";
import { parseTags } from "@/utils/tag-parser";
import { discussionsAPI, likesAPI, repoAPI } from "@/utils/api";
import { classifyError, classifyResponse } from "@/utils/http-errors";
import { resolveRepoTreeEntryPath } from "@/utils/repo-paths";
import MarkdownViewer from "@/components/common/MarkdownViewer.vue";
import MetadataHeader from "@/components/repo/metadata/MetadataHeader.vue";
import DetailedMetadataPanel from "@/components/repo/metadata/DetailedMetadataPanel.vue";
import ReferencedDatasetsCard from "@/components/repo/metadata/ReferencedDatasetsCard.vue";
import SidebarRelationshipsCard from "@/components/repo/metadata/SidebarRelationshipsCard.vue";
import DatasetViewerTab from "@/components/repo/DatasetViewerTab.vue";
import SpaceRuntimePanel from "@/components/repo/SpaceRuntimePanel.vue";
import QuickEvaluationPanel from "@/components/repo/QuickEvaluationPanel.vue";
import RepoMlflowPanel from "@/components/repo/RepoMlflowPanel.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import FilePreviewDialog from "@/components/repo/preview/FilePreviewDialog.vue";
import TarBrowserDialog from "@/components/repo/preview/TarBrowserDialog.vue";
import {
  buildResolveUrl,
  canPreviewFile,
  getPreviewKind,
} from "@/utils/file-preview";
import { tarSidecarPath } from "@/utils/indexed-tar";

const FILE_LIST_BATCH_SIZE = 50;

const props = defineProps({
  repoType: { type: String, required: true },
  namespace: { type: String, required: true },
  name: { type: String, required: true },
  branch: { type: String, default: "main" },
  currentPath: { type: String, default: "" },
  tab: { type: String, default: "card" },
});

const router = useRouter();
const authStore = useAuthStore();

const loading = ref(true);
const error = ref(null);
const repoInfo = ref(null);
const currentBranch = ref(props.branch);
const fileTree = ref([]);
const commits = ref([]);
const commitsLoading = ref(false);
const commitsHasMore = ref(false);
const commitsNextCursor = ref(null);
const filesLoading = ref(true);
const treeErrorClassification = ref(null);
const readmeErrorClassification = ref(null);
const readmeContent = ref("");
const readmeLoading = ref(true);
const readmeMetadata = ref({});
const fileSearchQuery = ref("");
const isLiked = ref(false);
const likesCount = ref(0);
const likingInProgress = ref(false);
const discussions = ref([]);
const discussionsLoading = ref(false);
const selectedDiscussionId = ref(null);
const selectedDiscussion = ref(null);
const discussionComments = ref([]);
const discussionDetailsLoading = ref(false);
const creatingDiscussion = ref(false);
const creatingComment = ref(false);
const deletingDiscussionId = ref(null);
const deletingCommentId = ref(null);
const newDiscussion = reactive({
  title: "",
  body: "",
});
const newCommentBody = ref("");
const deletingFolder = ref(false);
const fileTreeRequestId = ref(0);
const fileListNextCursor = ref(null);
const fileListLoadingMore = ref(false);
const fileListHasMore = computed(() => fileListNextCursor.value !== null);
const confirmedIndexedTars = ref(new Set());
const rejectedIndexedTars = ref(new Set());
let pendingIndexedTarProbeId = 0;

const previewDialogVisible = ref(false);
const previewTarget = ref(null);
const tarBrowserDialogVisible = ref(false);
const tarBrowserTarget = ref(null);

const PREVIEW_ICON_BY_KIND = {
  safetensors: "i-carbon-chart-line-data",
  parquet: "i-carbon-chart-line-data",
  "indexed-tar": "i-carbon-archive",
};

function previewIconClass(file) {
  const kind = getPreviewKind(
    file.path,
    fileTree.value,
    confirmedIndexedTars.value,
  );
  return PREVIEW_ICON_BY_KIND[kind] || "i-carbon-chart-line-data";
}

function previewIconTitle(file) {
  const kind = getPreviewKind(
    file.path,
    fileTree.value,
    confirmedIndexedTars.value,
  );
  if (kind === "indexed-tar") {
    return "浏览已索引 tar 内容（按需读取，不下载整包）";
  }
  return `预览 ${kind} 元数据（按需读取，不下载）`;
}

function canPreviewFileRow(file) {
  return canPreviewFile(file, fileTree.value, confirmedIndexedTars.value);
}

function buildResolveForPath(path) {
  return buildResolveUrl({
    baseUrl,
    repoType: props.repoType,
    namespace: props.namespace,
    name: props.name,
    branch: currentBranch.value,
    path,
  });
}

function openFilePreview(file) {
  const kind = getPreviewKind(
    file.path,
    fileTree.value,
    confirmedIndexedTars.value,
  );
  if (!kind) return;
  if (kind === "indexed-tar") {
    const dot = file.path.lastIndexOf(".");
    const indexPath = `${file.path.slice(0, dot)}.json`;
    tarBrowserTarget.value = {
      tarUrl: buildResolveForPath(file.path),
      indexUrl: buildResolveForPath(indexPath),
      filename: getFileName(file.path),
      tarTreeEntry: file,
    };
    tarBrowserDialogVisible.value = true;
    return;
  }
  previewTarget.value = {
    kind,
    resolveUrl: buildResolveForPath(file.path),
    filename: getFileName(file.path),
  };
  previewDialogVisible.value = true;
}

const baseUrl = window.location.origin;
const PATHS_INFO_BATCH_SIZE = 1000;

const activeTab = computed(() => props.tab);

const repoTypeLabel = computed(() => {
  const labels = { model: "模型", dataset: "数据集", space: "空间" };
  return labels[props.repoType] || "模型";
});

const repoDisplayTitle = computed(() => {
  if (props.repoType !== "dataset") return repoInfo.value?.id;
  return repoInfo.value?.name || props.name;
});

const isOwner = computed(() => {
  return authStore.canWriteToNamespace(props.namespace);
});

const isNamespaceOrg = ref(false);

const namespaceLink = computed(() => {
  if (isNamespaceOrg.value) {
    return `/organizations/${props.namespace}`;
  }
  return `/${props.namespace}`;
});

const pathSegments = computed(() => {
  return props.currentPath ? props.currentPath.split("/").filter(Boolean) : [];
});

const parsedTags = computed(() => {
  return parseTags(repoInfo.value?.tags || []);
});

const referencedDatasets = computed(() => {
  return parsedTags.value.datasets;
});

const cleanTags = computed(() => {
  return parsedTags.value.cleanTags;
});

const showTagsCard = computed(() => {
  return cleanTags.value.length > 0;
});

const showReferencedDatasetsCard = computed(() => {
  return referencedDatasets.value.length > 0;
});

const hasMetadataHeader = computed(() => {
  return (
    readmeMetadata.value.license ||
    readmeMetadata.value.language ||
    readmeMetadata.value.library_name ||
    readmeMetadata.value.pipeline_tag ||
    readmeMetadata.value.cn_model ||
    readmeMetadata.value.eval_results_chinese ||
    readmeMetadata.value.task_categories ||
    readmeMetadata.value.size_categories
  );
});

const hasDetailedMetadata = computed(() => {
  return Object.keys(readmeMetadata.value).length > 0;
});

const isExternalRepo = computed(() => {
  return repoInfo.value?._source && repoInfo.value._source !== "local";
});

const externalSourceName = computed(() => {
  return repoInfo.value?._source || "外部来源";
});

function getIconClass(type) {
  const icons = {
    model: "i-carbon-model text-blue-500",
    dataset: "i-carbon-data-table text-green-500",
    space: "i-carbon-application text-purple-500",
  };
  return icons[type] || icons.model;
}

function openExternalRepo() {
  if (!repoInfo.value?._source_url) return;

  const isHF =
    repoInfo.value._source &&
    (repoInfo.value._source.toLowerCase().includes("huggingface") ||
      repoInfo.value._source_url.includes("huggingface.co"));

  let url;
  if (isHF) {
    if (props.repoType === "model") {
      url = `${repoInfo.value._source_url}/${props.namespace}/${props.name}`;
    } else {
      url = `${repoInfo.value._source_url}/${props.repoType}s/${props.namespace}/${props.name}`;
    }
  } else {
    url = `${repoInfo.value._source_url}/${props.repoType}s/${props.namespace}/${props.name}`;
  }

  window.open(url, "_blank");
}

function formatDate(date) {
  return formatRelativeTime(date, "未知");
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return "-";
  if (bytes < 1000) return bytes + " B";
  if (bytes < 1000 * 1000) return (bytes / 1000).toFixed(1) + " KB";
  if (bytes < 1000 * 1000 * 1000) {
    return (bytes / (1000 * 1000)).toFixed(1) + " MB";
  }
  return (bytes / (1000 * 1000 * 1000)).toFixed(1) + " GB";
}

function formatEntrySize(file) {
  return formatSize(file.size);
}

function getEntryCommitTitle(file) {
  return file.lastCommit?.title || "-";
}

function getEntryUpdatedAt(file) {
  return formatRelativeTime(file.lastCommit?.date || file.lastModified, "-");
}

function getFileName(path) {
  const parts = path.split("/");
  return parts[parts.length - 1] || path;
}

function sortFileEntries(entries) {
  return [...entries].sort((a, b) => {
    if (a.type === "directory" && b.type !== "directory") return -1;
    if (a.type !== "directory" && b.type === "directory") return 1;
    return a.path.localeCompare(b.path);
  });
}

function chunkPaths(paths, size) {
  const chunks = [];
  for (let index = 0; index < paths.length; index += size) {
    chunks.push(paths.slice(index, index + size));
  }
  return chunks;
}

function navigateToTab(tab) {
  switch (tab) {
    case "files":
      router.push(
        `/${props.repoType}s/${props.namespace}/${props.name}/tree/${currentBranch.value}`,
      );
      break;
    case "commits":
      router.push(
        `/${props.repoType}s/${props.namespace}/${props.name}/commits/${currentBranch.value}`,
      );
      break;
    case "metadata":
      router.push({
        path: `/${props.repoType}s/${props.namespace}/${props.name}`,
        query: { tab: "metadata" },
      });
      break;
    case "discussions":
      router.push({
        path: `/${props.repoType}s/${props.namespace}/${props.name}`,
        query: { tab: "discussions" },
      });
      break;
    case "viewer":
      router.push({
        path: `/${props.repoType}s/${props.namespace}/${props.name}`,
        query: { tab: "viewer" },
      });
      break;
    case "runtime":
      router.push({
        path: `/${props.repoType}s/${props.namespace}/${props.name}`,
        query: { tab: "runtime" },
      });
      break;
    case "evaluations":
      router.push({
        path: `/${props.repoType}s/${props.namespace}/${props.name}`,
        query: { tab: "evaluations" },
      });
      break;
    default:
      router.push(`/${props.repoType}s/${props.namespace}/${props.name}`);
  }
}

function navigateToSettings() {
  router.push(`/${props.repoType}s/${props.namespace}/${props.name}/settings`);
}

function navigateToUpload() {
  router.push(
    `/${props.repoType}s/${props.namespace}/${props.name}/upload/${currentBranch.value}`,
  );
}

function getCommitPath(commitId) {
  return `/${props.repoType}s/${props.namespace}/${props.name}/commit/${commitId}`;
}

function viewCommit(commitId) {
  router.push(getCommitPath(commitId));
}

function handleBranchChange() {
  if (activeTab.value === "files") {
    router.push(
      `/${props.repoType}s/${props.namespace}/${props.name}/tree/${currentBranch.value}`,
    );
  }
}

async function checkIfNamespaceIsOrg() {
  try {
    const { data } = await axios.get(`/api/users/${props.namespace}/type`, {
      params: { fallback: true },
    });
    isNamespaceOrg.value = data.type === "org";
  } catch {
    isNamespaceOrg.value = false;
  }
}

async function loadRepoInfo() {
  loading.value = true;
  error.value = null;

  try {
    const { data } = await repoAPI.getInfo(
      props.repoType,
      props.namespace,
      props.name,
    );
    repoInfo.value = data;
    likesCount.value = data.likes || 0;

    checkIfNamespaceIsOrg();

    if (authStore.isAuthenticated) {
      try {
        const { data: likeData } = await likesAPI.checkLiked(
          props.repoType,
          props.namespace,
          props.name,
        );
        isLiked.value = likeData.liked;
      } catch (err) {
        console.error("Failed to check liked status:", err);
      }
    }
  } catch (err) {
    error.value = err.response?.data?.detail || "加载仓库失败";
    console.error("Failed to load repo info:", err);
  } finally {
    loading.value = false;
  }
}

function handleMlflowBindingUpdated(binding) {
  if (!repoInfo.value) return;
  repoInfo.value = {
    ...repoInfo.value,
    mlflow: binding,
  };
}

async function toggleLike() {
  if (!authStore.isAuthenticated) {
    ElMessage.warning("请先登录后再点赞仓库");
    return;
  }

  if (likingInProgress.value) return;

  likingInProgress.value = true;

  try {
    if (isLiked.value) {
      const { data } = await likesAPI.unlike(
        props.repoType,
        props.namespace,
        props.name,
      );
      isLiked.value = false;
      likesCount.value = data.likes_count;
      ElMessage.success("已取消点赞");
    } else {
      const { data } = await likesAPI.like(
        props.repoType,
        props.namespace,
        props.name,
      );
      isLiked.value = true;
      likesCount.value = data.likes_count;
      ElMessage.success("已点赞");
    }
  } catch (err) {
    console.error("Failed to toggle like:", err);
    const errorMsg =
      err.response?.data?.detail?.error || "更新点赞状态失败";
    ElMessage.error(errorMsg);
  } finally {
    likingInProgress.value = false;
  }
}

function activeNamePrefix() {
  const value = fileSearchQuery.value;
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed || null;
}

async function expandPathsInfoAndMerge(newEntries, requestId) {
  if (!newEntries.length) return;

  try {
    const pathInfoByPath = new Map();
    const pathBatches = chunkPaths(
      newEntries.map((file) => file.path),
      PATHS_INFO_BATCH_SIZE,
    );

    for (const pathBatch of pathBatches) {
      const { data: expandedEntries } = await repoAPI.getPathsInfo(
        props.repoType,
        props.namespace,
        props.name,
        currentBranch.value,
        pathBatch,
        true,
      );

      if (requestId !== fileTreeRequestId.value) return;

      for (const entry of expandedEntries || []) {
        pathInfoByPath.set(entry.path, entry);
      }
    }

    if (requestId !== fileTreeRequestId.value) return;

    const newPaths = new Set(newEntries.map((file) => file.path));
    fileTree.value = fileTree.value.map((file) => {
      if (!newPaths.has(file.path)) return file;
      const expanded = pathInfoByPath.get(file.path);
      return expanded ? { ...file, ...expanded } : file;
    });
  } catch (err) {
    console.error("Failed to load expanded path info:", err);
  }
}

async function loadFileTree({ resetPagination = true } = {}) {
  if (resetPagination) {
    fileListNextCursor.value = null;
  }
  filesLoading.value = true;
  treeErrorClassification.value = null;
  const requestId = fileTreeRequestId.value + 1;
  fileTreeRequestId.value = requestId;

  let sortedEntries = [];
  const namePrefix = activeNamePrefix();

  try {
    const page = await repoAPI.listTreePage(
      props.repoType,
      props.namespace,
      props.name,
      currentBranch.value,
      props.currentPath ? `/${props.currentPath}` : "",
      {
        recursive: false,
        limit: FILE_LIST_BATCH_SIZE,
        name_prefix: namePrefix || undefined,
      },
    );

    if (requestId !== fileTreeRequestId.value) return;

    sortedEntries = sortFileEntries(page.entries || []);
    fileTree.value = sortedEntries;
    fileListNextCursor.value = page.nextCursor || null;

    if (sortedEntries.length === 0) {
      return;
    }
  } catch (err) {
    console.error("Failed to load file tree:", err);
    if (requestId === fileTreeRequestId.value) {
      fileTree.value = [];
      fileListNextCursor.value = null;
      treeErrorClassification.value =
        err?.classification || classifyError(err);
    }
  } finally {
    if (requestId === fileTreeRequestId.value) {
      filesLoading.value = false;
    }
  }

  if (sortedEntries.length === 0 || requestId !== fileTreeRequestId.value) {
    return;
  }

  resetIndexedTarProbeMemo();
  void probeMissingIndexedTarSiblings(sortedEntries, requestId);
  await expandPathsInfoAndMerge(sortedEntries, requestId);
}

async function loadMoreFileTree() {
  if (fileListLoadingMore.value || filesLoading.value) return;
  if (!fileListNextCursor.value) return;

  fileListLoadingMore.value = true;
  const requestId = fileTreeRequestId.value + 1;
  fileTreeRequestId.value = requestId;

  let appendedEntries = [];
  const cursor = fileListNextCursor.value;
  const namePrefix = activeNamePrefix();

  try {
    const page = await repoAPI.listTreePage(
      props.repoType,
      props.namespace,
      props.name,
      currentBranch.value,
      props.currentPath ? `/${props.currentPath}` : "",
      {
        recursive: false,
        limit: FILE_LIST_BATCH_SIZE,
        cursor,
        name_prefix: namePrefix || undefined,
      },
    );

    if (requestId !== fileTreeRequestId.value) return;

    appendedEntries = page.entries || [];
    fileTree.value = sortFileEntries([...fileTree.value, ...appendedEntries]);
    fileListNextCursor.value = page.nextCursor || null;
  } catch (err) {
    console.error("Failed to load more file tree entries:", err);
  } finally {
    if (requestId === fileTreeRequestId.value) {
      fileListLoadingMore.value = false;
    }
  }

  if (!appendedEntries.length || requestId !== fileTreeRequestId.value) {
    return;
  }

  void probeMissingIndexedTarSiblings(appendedEntries, requestId);
  await expandPathsInfoAndMerge(appendedEntries, requestId);
}

function resetIndexedTarProbeMemo() {
  pendingIndexedTarProbeId += 1;
  confirmedIndexedTars.value = new Set();
  rejectedIndexedTars.value = new Set();
}

async function probeMissingIndexedTarSiblings(entries, requestId) {
  const probeId = pendingIndexedTarProbeId;
  const loadedSiblings = new Set(
    fileTree.value
      .filter((entry) => entry && entry.type !== "directory")
      .map((entry) => entry.path),
  );

  const pending = [];
  for (const entry of entries) {
    if (!entry || entry.type === "directory") continue;
    const sidecar = tarSidecarPath(entry.path);
    if (!sidecar) continue;
    if (loadedSiblings.has(sidecar)) continue;
    if (confirmedIndexedTars.value.has(entry.path)) continue;
    if (rejectedIndexedTars.value.has(entry.path)) continue;
    pending.push({ tarPath: entry.path, sidecar });
  }
  if (pending.length === 0) return;

  await Promise.all(
    pending.map(async ({ tarPath, sidecar }) => {
      const exists = await repoAPI.fileExists(
        props.repoType,
        props.namespace,
        props.name,
        currentBranch.value,
        sidecar,
      );
      if (
        probeId !== pendingIndexedTarProbeId ||
        requestId !== fileTreeRequestId.value
      ) {
        return;
      }
      if (exists) {
        const next = new Set(confirmedIndexedTars.value);
        next.add(tarPath);
        confirmedIndexedTars.value = next;
      } else {
        const next = new Set(rejectedIndexedTars.value);
        next.add(tarPath);
        rejectedIndexedTars.value = next;
      }
    }),
  );
}

async function loadReadme() {
  readmeLoading.value = true;
  readmeErrorClassification.value = null;
  try {
    let readmeFile = fileTree.value.find(
      (f) => f.type === "file" && f.path.toLowerCase().endsWith("readme.md"),
    );

    if (!readmeFile) {
      readmeFile = await findReadmeViaPathsInfo();
    }

    if (!readmeFile) {
      readmeContent.value = "";
      readmeMetadata.value = {};
      return;
    }

    const downloadUrl = `/${props.repoType}s/${props.namespace}/${props.name}/resolve/${currentBranch.value}/${readmeFile.path}`;
    const response = await fetch(downloadUrl);

    if (response.ok) {
      const rawContent = await response.text();
      const { metadata, content } = parseYAMLFrontmatter(rawContent);
      readmeMetadata.value = normalizeMetadata(metadata);
      readmeContent.value = content ? content : " ";
    } else {
      readmeErrorClassification.value = await classifyResponse(response);
      readmeContent.value = "";
      readmeMetadata.value = {};
    }
  } catch (err) {
    console.error("Failed to load README:", err);
    readmeErrorClassification.value =
      err?.classification || classifyError(err);
    readmeContent.value = "";
    readmeMetadata.value = {};
  } finally {
    readmeLoading.value = false;
  }
}

async function findReadmeViaPathsInfo() {
  if (props.currentPath) return null;
  try {
    const { data } = await repoAPI.getPathsInfo(
      props.repoType,
      props.namespace,
      props.name,
      currentBranch.value,
      ["README.md", "readme.md", "Readme.md"],
      false,
    );
    return (data || []).find((entry) => entry && entry.type === "file") || null;
  } catch (err) {
    console.debug("README paths-info probe failed:", err);
    return null;
  }
}

async function loadCommits() {
  commitsLoading.value = true;
  try {
    const { data } = await repoAPI.listCommits(
      props.repoType,
      props.namespace,
      props.name,
      currentBranch.value,
      { limit: 20 },
    );

    commits.value = data.commits || [];
    commitsHasMore.value = data.hasMore || false;
    commitsNextCursor.value = data.nextCursor || null;
  } catch (err) {
    console.error("Failed to load commits:", err);
    commits.value = [];
  } finally {
    commitsLoading.value = false;
  }
}

async function loadMoreCommits() {
  if (!commitsHasMore.value || commitsLoading.value) return;

  commitsLoading.value = true;
  try {
    const { data } = await repoAPI.listCommits(
      props.repoType,
      props.namespace,
      props.name,
      currentBranch.value,
      { limit: 20, after: commitsNextCursor.value },
    );

    commits.value.push(...(data.commits || []));
    commitsHasMore.value = data.hasMore || false;
    commitsNextCursor.value = data.nextCursor || null;
  } catch (err) {
    console.error("Failed to load more commits:", err);
  } finally {
    commitsLoading.value = false;
  }
}

async function loadDiscussions() {
  if (isExternalRepo.value) return;

  discussionsLoading.value = true;
  try {
    const { data } = await discussionsAPI.list(
      props.repoType,
      props.namespace,
      props.name,
      { limit: 100 },
    );
    discussions.value = data.discussions || [];
    if (!selectedDiscussionId.value && discussions.value.length > 0) {
      selectedDiscussionId.value = discussions.value[0].id;
      await loadDiscussion(selectedDiscussionId.value);
    } else if (
      selectedDiscussionId.value &&
      discussions.value.some((item) => item.id === selectedDiscussionId.value)
    ) {
      await loadDiscussion(selectedDiscussionId.value);
    } else if (discussions.value.length === 0) {
      selectedDiscussionId.value = null;
      selectedDiscussion.value = null;
      discussionComments.value = [];
    }
  } catch (err) {
    console.error("Failed to load discussions:", err);
    ElMessage.error("加载讨论失败");
  } finally {
    discussionsLoading.value = false;
  }
}

async function loadDiscussion(discussionId) {
  if (!discussionId) return;

  discussionDetailsLoading.value = true;
  try {
    const { data } = await discussionsAPI.get(
      props.repoType,
      props.namespace,
      props.name,
      discussionId,
    );
    selectedDiscussion.value = data.discussion;
    discussionComments.value = data.comments || [];
  } catch (err) {
    console.error("Failed to load discussion:", err);
    ElMessage.error("加载讨论详情失败");
  } finally {
    discussionDetailsLoading.value = false;
  }
}

async function selectDiscussion(discussionId) {
  selectedDiscussionId.value = discussionId;
  await loadDiscussion(discussionId);
}

async function submitDiscussion() {
  const title = newDiscussion.title.trim();
  const body = newDiscussion.body.trim();
  if (!title || !body) {
    ElMessage.warning("请填写标题和正文");
    return;
  }

  creatingDiscussion.value = true;
  try {
    const { data } = await discussionsAPI.create(
      props.repoType,
      props.namespace,
      props.name,
      { title, body },
    );
    newDiscussion.title = "";
    newDiscussion.body = "";
    ElMessage.success("讨论已发布");
    selectedDiscussionId.value = data.id;
    await loadDiscussions();
  } catch (err) {
    console.error("Failed to create discussion:", err);
    ElMessage.error(err.response?.data?.detail?.error || "发布讨论失败");
  } finally {
    creatingDiscussion.value = false;
  }
}

async function submitComment() {
  const body = newCommentBody.value.trim();
  if (!selectedDiscussionId.value || !body) {
    ElMessage.warning("请填写回复内容");
    return;
  }

  creatingComment.value = true;
  try {
    await discussionsAPI.createComment(
      props.repoType,
      props.namespace,
      props.name,
      selectedDiscussionId.value,
      { body },
    );
    newCommentBody.value = "";
    ElMessage.success("回复已发布");
    await loadDiscussions();
  } catch (err) {
    console.error("Failed to create comment:", err);
    ElMessage.error(err.response?.data?.detail?.error || "发布回复失败");
  } finally {
    creatingComment.value = false;
  }
}

function canDeleteDiscussion(discussion) {
  if (!authStore.isAuthenticated || !discussion?.author) return false;
  return discussion.author.username === authStore.username || isOwner.value;
}

function canDeleteComment(comment) {
  if (!authStore.isAuthenticated || !comment?.author) return false;
  return comment.author.username === authStore.username || isOwner.value;
}

async function confirmDeleteDiscussion(discussion) {
  try {
    await ElMessageBox.confirm(
      `确定要删除讨论“${discussion.title}”吗？相关回复也会一起删除。`,
      "删除讨论",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        confirmButtonClass: "el-button--danger",
      },
    );
    await deleteDiscussion(discussion.id);
  } catch {
    // no-op
  }
}

async function deleteDiscussion(discussionId) {
  deletingDiscussionId.value = discussionId;
  try {
    await discussionsAPI.deleteDiscussion(
      props.repoType,
      props.namespace,
      props.name,
      discussionId,
    );
    ElMessage.success("讨论已删除");
    if (selectedDiscussionId.value === discussionId) {
      selectedDiscussionId.value = null;
      selectedDiscussion.value = null;
      discussionComments.value = [];
    }
    await loadDiscussions();
  } catch (err) {
    console.error("Failed to delete discussion:", err);
    ElMessage.error(err.response?.data?.detail?.error || "删除讨论失败");
  } finally {
    deletingDiscussionId.value = null;
  }
}

async function confirmDeleteComment(comment) {
  try {
    await ElMessageBox.confirm("确定要删除这条回复吗？", "删除回复", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
      confirmButtonClass: "el-button--danger",
    });
    await deleteComment(comment.id);
  } catch {
    // no-op
  }
}

async function deleteComment(commentId) {
  deletingCommentId.value = commentId;
  try {
    await discussionsAPI.deleteComment(
      props.repoType,
      props.namespace,
      props.name,
      selectedDiscussionId.value,
      commentId,
    );
    ElMessage.success("回复已删除");
    await loadDiscussions();
  } catch (err) {
    console.error("Failed to delete comment:", err);
    ElMessage.error(err.response?.data?.detail?.error || "删除回复失败");
  } finally {
    deletingCommentId.value = null;
  }
}

function getEntryHref(file) {
  const targetPath = resolveRepoTreeEntryPath(props.currentPath, file.path);
  const kind = file.type === "directory" ? "tree" : "blob";
  return `/${props.repoType}s/${props.namespace}/${props.name}/${kind}/${currentBranch.value}/${targetPath}`;
}

function downloadRepo() {
  if (isExternalRepo.value) {
    ElMessage.warning("外部仓库请前往源站下载");
    openExternalRepo();
    return;
  }

  const revision = encodeURIComponent(currentBranch.value || "main");
  const namespace = encodeURIComponent(props.namespace);
  const name = encodeURIComponent(props.name);
  const url = `/api/${props.repoType}s/${namespace}/${name}/archive/${revision}`;
  const link = document.createElement("a");
  link.href = url;
  link.download = `${props.name}-${currentBranch.value || "main"}.zip`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  ElMessage.success("已开始打包下载");
}

function formatCommitDate(timestamp) {
  return formatUnixRelativeTime(timestamp, "未知");
}

function getProgressColor(percentage) {
  if (percentage >= 90) return "#f56c6c";
  if (percentage >= 75) return "#e6a23c";
  return "#67c23a";
}

async function createReadme() {
  try {
    const readmeContent = `# ${props.name}\n\n在这里添加项目说明。\n`;

    const result = await repoAPI.commitFiles(
      props.repoType,
      props.namespace,
      props.name,
      currentBranch.value,
      {
        message: "创建 README.md",
        files: [
          {
            path: "README.md",
            content: readmeContent,
          },
        ],
      },
    );

    console.log("Commit result:", result);
    ElMessage.success("README.md 创建成功");

    await loadFileTree();
    await loadReadme();
  } catch (err) {
    console.error("Failed to create README:", err);
    console.error("Error response:", err.response);
    console.error("Error data:", err.response?.data);
    const errorMsg =
      err.response?.data?.detail?.error || "创建 README.md 失败";
    ElMessage.error(errorMsg);
  }
}

async function copyRepoId() {
  const repoId = `${props.namespace}/${props.name}`;
  const success = await copyToClipboard(repoId);
  if (success) {
    ElMessage.success("仓库 ID 已复制");
  } else {
    ElMessage.error("复制失败");
  }
}

async function confirmDeleteFolder() {
  const folderName = pathSegments.value[pathSegments.value.length - 1];
  try {
    await ElMessageBox.confirm(
      `确定要删除文件夹“${folderName}”及其中全部内容吗？此操作无法撤销。`,
      "删除文件夹",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        confirmButtonClass: "el-button--danger",
      },
    );

    await deleteFolder();
  } catch {
    // no-op
  }
}

async function deleteFolder() {
  deletingFolder.value = true;

  try {
    await repoAPI.commitFiles(
      props.repoType,
      props.namespace,
      props.name,
      currentBranch.value,
      {
        message: `删除文件夹 ${props.currentPath}`,
        operations: [
          {
            operation: "deletedFolder",
            path: props.currentPath,
          },
        ],
      },
    );

    const folderName = pathSegments.value[pathSegments.value.length - 1];
    ElMessage.success(`文件夹“${folderName}”已删除`);

    if (pathSegments.value.length > 1) {
      const parentPath = pathSegments.value.slice(0, -1).join("/");
      router.push(
        `/${props.repoType}s/${props.namespace}/${props.name}/tree/${currentBranch.value}/${parentPath}`,
      );
    } else {
      router.push(
        `/${props.repoType}s/${props.namespace}/${props.name}/tree/${currentBranch.value}`,
      );
    }
  } catch (err) {
    console.error("Failed to delete folder:", err);
    const errorMsg =
      err.response?.data?.detail?.error || "删除文件夹失败";
    ElMessage.error(errorMsg);
  } finally {
    deletingFolder.value = false;
  }
}

const FILE_SEARCH_DEBOUNCE_MS = 300;
let fileSearchDebounceHandle = null;
watch(fileSearchQuery, () => {
  if (fileSearchDebounceHandle) {
    clearTimeout(fileSearchDebounceHandle);
  }
  fileSearchDebounceHandle = setTimeout(() => {
    fileSearchDebounceHandle = null;
    if (activeTab.value === "files" || activeTab.value === "card") {
      loadFileTree({ resetPagination: true });
    }
  }, FILE_SEARCH_DEBOUNCE_MS);
});

watch(
  () => props.currentPath,
  () => {
    if (activeTab.value === "files") {
      loadFileTree();
    }
  },
);

watch(
  () => props.branch,
  (newBranch) => {
    currentBranch.value = newBranch;
    if (activeTab.value === "files") {
      loadFileTree();
    }
  },
);

watch(
  () => props.tab,
  async (newTab) => {
    if (newTab === "files" && fileTree.value.length === 0) {
      await loadFileTree();
    } else if (newTab === "card" && !readmeContent.value) {
      if (fileTree.value.length === 0) {
        await loadFileTree();
      }
      await loadReadme();
    } else if (newTab === "commits" && commits.value.length === 0) {
      await loadCommits();
    } else if (newTab === "discussions" && discussions.value.length === 0) {
      await loadDiscussions();
    }
  },
);

watch(
  fileTree,
  () => {
    if (activeTab.value === "card" && !readmeContent.value) {
      loadReadme();
    }
  },
  { immediate: false },
);

onMounted(async () => {
  await loadRepoInfo();

  if (activeTab.value === "files") {
    await loadFileTree();
  } else if (activeTab.value === "card") {
    await loadFileTree();
    await loadReadme();
  } else if (activeTab.value === "viewer") {
    await loadFileTree();
  } else if (activeTab.value === "commits") {
    await loadCommits();
  } else if (activeTab.value === "discussions") {
    await loadDiscussions();
  }
});
</script>
