<script setup lang="ts">
// Purely illustrative mock of the workspace — not wired to real state. It
// exists to show what "upload, pick a tool, download" looks like before a
// visitor has uploaded anything.
const tools = [
  { name: 'Merge', icon: 'i-lucide-combine' },
  { name: 'Compress', icon: 'i-lucide-minimize-2' },
  { name: 'Split', icon: 'i-lucide-scissors' },
  { name: 'Watermark', icon: 'i-lucide-stamp' },
  { name: 'Protect', icon: 'i-lucide-lock' },
] as const

const formats = ['PDF', 'DOCX', 'PNG', 'JPG', 'PPTX']
</script>

<template>
  <div class="panel overflow-hidden">
    <div class="flex items-center gap-3 border-b border-ink-800 px-4 py-3">
      <span class="flex size-5 items-center justify-center rounded-xs bg-accent-400 font-mono text-[10px] font-bold text-ink-950">P</span>
      <span class="font-mono text-xs text-ink-400">workspace.pdfflow</span>
      <span class="ml-auto inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-widest text-ink-400">
        <span class="size-1.5 rounded-full bg-accent-400" aria-hidden="true" />
        Live preview
      </span>
    </div>

    <div class="grid sm:grid-cols-[152px_1fr]">
      <div class="space-y-1 border-b border-ink-800 p-3 sm:border-b-0 sm:border-r">
        <p class="px-2 pb-1 font-mono text-[10px] uppercase tracking-widest text-ink-700">Tools</p>
        <div
          v-for="(tool, i) in tools"
          :key="tool.name"
          class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm"
          :class="i === 1 ? 'bg-accent-500/10 text-accent-600' : 'text-ink-400'"
        >
          <span class="font-mono text-[10px] text-ink-700">{{ String(i + 1).padStart(2, '0') }}</span>
          <UIcon :name="tool.icon" class="size-4" />
          {{ tool.name }}
        </div>
      </div>

      <div class="space-y-4 p-5">
        <div class="flex items-center gap-3">
          <UIcon name="i-lucide-file-text" class="size-8 shrink-0 text-accent-600" />
          <div class="min-w-0">
            <p class="truncate text-sm font-medium text-ink-200">quarterly-report.pdf</p>
            <p class="text-xs text-ink-400">18 pages</p>
          </div>
        </div>

        <div class="rounded-md border-l-2 border-accent-400 bg-accent-500/10 px-4 py-3">
          <p class="text-sm font-medium text-ink-200">Compress</p>
          <p class="mt-0.5 text-sm text-ink-400">Shrinks file size while keeping pages sharp enough to read.</p>
        </div>

        <div>
          <p class="mb-2 font-mono text-[10px] uppercase tracking-widest text-ink-700">Supported formats</p>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="format in formats"
              :key="format"
              class="rounded-md border border-ink-800 px-2 py-0.5 font-mono text-xs text-ink-400"
            >{{ format }}</span>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-3 border-t border-ink-800 pt-4">
          <div>
            <p class="text-xl font-bold text-ink-950">12.4<span class="text-sm font-normal text-ink-400">MB</span></p>
            <p class="text-xs text-ink-400">Original</p>
          </div>
          <div>
            <p class="text-xl font-bold text-ink-950">3.9<span class="text-sm font-normal text-ink-400">MB</span></p>
            <p class="text-xs text-ink-400">Compressed</p>
          </div>
          <div>
            <p class="text-xl font-bold text-accent-600">68%</p>
            <p class="text-xs text-ink-400">Smaller</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
