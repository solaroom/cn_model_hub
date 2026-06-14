<template>
  <footer class="mt-10 border-t border-slate-200/70 bg-white/70 dark:border-slate-800 dark:bg-slate-950/70">
    <div class="container-main py-10">
      <div class="grid gap-8 md:grid-cols-[1.5fr_repeat(4,1fr)]">
        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <img
              src="/images/logo-square.svg"
              alt="中文开源AI模型社区"
              class="h-10 w-10 rounded-lg"
            />
            <div>
              <div class="font-semibold">中文开源AI模型社区</div>
              <div class="text-sm text-slate-500 dark:text-slate-400">
                面向中文开源 AI 模型的课程实践平台。
              </div>
            </div>
          </div>
          <div class="text-sm text-slate-500 dark:text-slate-400">
            覆盖模型托管、数据集管理、在线 Demo、社区讨论和中文评测基准。
          </div>
        </div>

        <div>
          <h3 class="mb-3 font-semibold">了解平台</h3>
          <div class="flex flex-col gap-2 text-sm text-slate-500 dark:text-slate-400">
            <a href="/docs" class="hover:text-blue-500">文档中心</a>
            <a href="/about" class="hover:text-blue-500">关于项目</a>
          </div>
        </div>

        <div>
          <h3 class="mb-3 font-semibold">快速开始</h3>
          <div class="flex flex-col gap-2 text-sm text-slate-500 dark:text-slate-400">
            <a href="/get-started" class="hover:text-blue-500">开始使用</a>
            <a href="/self-hosted" class="hover:text-blue-500">自托管部署</a>
          </div>
        </div>

        <div>
          <h3 class="mb-3 font-semibold">项目功能</h3>
          <div class="flex flex-col gap-2 text-sm text-slate-500 dark:text-slate-400">
            <a href="/models" class="hover:text-blue-500">模型广场</a>
            <a href="/datasets" class="hover:text-blue-500">数据集</a>
            <a href="/spaces" class="hover:text-blue-500">在线 Demo</a>
          </div>
        </div>

        <div>
          <h3 class="mb-3 font-semibold">条款</h3>
          <div class="flex flex-col gap-2 text-sm text-slate-500 dark:text-slate-400">
            <a href="/terms" class="hover:text-blue-500">服务条款</a>
            <a href="/privacy" class="hover:text-blue-500">隐私说明</a>
          </div>
        </div>
      </div>

      <div
        class="mt-8 border-t border-slate-200/70 pt-6 text-center text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400"
      >
        © 2026 中文开源AI模型社区，课程项目演示版本。
      </div>
    </div>
  </footer>
</template>
