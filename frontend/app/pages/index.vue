<script setup lang="ts">
import type { Operation } from '~/types/api'

const api = useApi()
const workspace = useWorkspaceStore()

const uploading = ref(false)
const uploadProgress = ref(0)
const error = ref<string | null>(null)

const { data: operations } = await useAsyncData<Operation[]>(
  'operations',
  () => api.operations(),
  { default: () => [] },
)

const categories = [
  { key: 'organize', label: 'Organise' },
  { key: 'optimize', label: 'Optimise' },
  { key: 'convert', label: 'Convert' },
  { key: 'security', label: 'Security' },
  { key: 'edit', label: 'Edit' },
] as const

async function handleFiles(files: File[]) {
  error.value = null
  uploading.value = true
  uploadProgress.value = 0
  try {
    const result = await api.upload(files, (percent) => {
      uploadProgress.value = percent
    })
    workspace.setUpload(result.files, result.availableOperations)
    await navigateTo('/workspace')
  } catch (err) {
    error.value = (err as Error).message
  } finally {
    uploading.value = false
  }
}

const promises = [
  {
    icon: 'i-lucide-user-x',
    title: 'No signup, ever',
    body: 'No email, no password, no cookie banner. Open the page and start working.',
  },
  {
    icon: 'i-lucide-shield-check',
    title: 'Private by design',
    body: 'Files are stored under a random name that only your browser session knows.',
  },
  {
    icon: 'i-lucide-timer',
    title: 'Deleted automatically',
    body: 'Everything you upload is erased within 30 minutes — usually much sooner.',
  },
]
</script>

<template>
  <div>
    <!-- Hero -->
    <section id="upload" class="relative scroll-mt-20 overflow-hidden px-6 pb-16 pt-20">
      <div class="grid-fade pointer-events-none absolute inset-0" aria-hidden="true" />
      <div class="relative mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[1.1fr_1fr]">
        <div>
          <span
            class="enter-rise inline-flex items-center gap-2 rounded-full border border-ink-800 px-3 py-1 font-mono text-xs uppercase tracking-widest text-ink-400"
          >
            <span class="size-1.5 rounded-xs bg-accent-400" aria-hidden="true" />
            {{ operations.length }} tools · zero accounts
          </span>

          <h1
            class="enter-rise mt-5 text-balance text-5xl font-black leading-[0.95] tracking-tight text-ink-950 sm:text-6xl"
            style="--enter-delay: 0.08s"
          >
            Your PDFs,
            <span class="block"><span class="highlight-mark">handled.</span></span>
          </h1>
          <p class="enter-rise mt-5 max-w-xl text-pretty text-lg text-ink-400" style="--enter-delay: 0.16s">
            Merge, split, compress and convert documents in seconds. Your files are
            processed and then deleted — nothing is kept, nothing is shared.
          </p>

          <div class="enter-rise mt-8" style="--enter-delay: 0.24s">
            <UploadPanel
              :uploading="uploading"
              :progress="uploadProgress"
              :error="error"
              @files="handleFiles"
              @error="error = $event"
              @dismiss="error = null"
            />
          </div>

          <ul
            class="enter-rise mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-ink-400"
            style="--enter-delay: 0.32s"
          >
            <li v-for="promise in promises" :key="promise.title" class="flex items-center gap-1.5">
              <UIcon :name="promise.icon" class="size-4 text-accent-600" />
              {{ promise.title }}
            </li>
          </ul>
        </div>

        <HeroPreview class="enter-drift hidden lg:block" style="--enter-delay: 0.2s" />
      </div>
    </section>

    <!-- Tools -->
    <section id="tools" class="mx-auto max-w-6xl scroll-mt-20 px-6 py-16">
      <div class="reveal">
        <span class="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-ink-400">
          <span class="size-1.5 rounded-xs bg-accent-400" aria-hidden="true" />
          Works with your files
        </span>
        <h2 class="mt-3 text-2xl font-semibold text-ink-950">Every tool you need</h2>
        <p class="mt-2 text-ink-400">
          Pick a file first — PDFFlow only offers the tools that fit what you uploaded.
        </p>
      </div>

      <div v-for="category in categories" :key="category.key" class="mt-10">
        <h3 class="mb-3 text-sm font-medium uppercase tracking-wider text-ink-400">
          {{ category.label }}
        </h3>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <ToolCard
            v-for="(operation, i) in operations.filter((op) => op.category === category.key)"
            :key="operation.key"
            :operation="operation"
            :index="i + 1"
          />
        </div>
      </div>
    </section>

    <!-- Privacy -->
    <section id="privacy" class="mx-auto max-w-6xl scroll-mt-20 px-6 py-16">
      <div class="panel reveal p-8 sm:p-12">
        <span class="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-ink-400">
          <span class="size-1.5 rounded-xs bg-accent-400" aria-hidden="true" />
          Made to stay out of your way
        </span>
        <h2 class="mt-3 text-2xl font-semibold text-ink-950">What happens to your files</h2>
        <p class="mt-2 max-w-2xl text-ink-400">
          Most PDF sites ask you to trust a privacy policy. Here is the actual
          lifecycle instead.
        </p>

        <ol class="mt-8 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <li
            v-for="(step, index) in [
              { title: 'Upload', body: 'Your file is written to a temporary directory under a random UUID name. Its original name is never used on disk.' },
              { title: 'Process', body: 'A background worker reads it, does the one operation you asked for, and writes the result.' },
              { title: 'Download', body: 'You fetch the result over a link tied to your job id. No index, no listing, no sharing.' },
              { title: 'Delete', body: 'Inputs are removed the moment the job ends; results within 30 minutes. A sweep runs every 5 minutes.' },
            ]"
            :key="step.title"
            class="space-y-1.5 border-t border-ink-800 pt-4"
          >
            <span class="block font-mono text-sm text-accent-600">{{ String(index + 1).padStart(2, '0') }}</span>
            <h3 class="font-medium text-ink-200">{{ step.title }}</h3>
            <p class="text-sm leading-relaxed text-ink-400">{{ step.body }}</p>
          </li>
        </ol>
      </div>
    </section>
  </div>
</template>
