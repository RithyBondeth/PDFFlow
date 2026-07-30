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
    <section class="mx-auto max-w-3xl px-6 pb-16 pt-20 text-center">
      <h1 class="text-balance text-5xl font-semibold tracking-tight text-white sm:text-6xl">
        Fast, private PDF tools.
        <span class="block text-accent-400">No signup required.</span>
      </h1>
      <p class="mx-auto mt-5 max-w-xl text-pretty text-lg text-ink-400">
        Merge, split, compress and convert documents in seconds. Your files are
        processed and then deleted — nothing is kept, nothing is shared.
      </p>

      <div class="mt-10">
        <UploadPanel
          :uploading="uploading"
          :progress="uploadProgress"
          :error="error"
          @files="handleFiles"
          @error="error = $event"
          @dismiss="error = null"
        />
      </div>

      <ul class="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-ink-400">
        <li v-for="promise in promises" :key="promise.title" class="flex items-center gap-1.5">
          <UIcon :name="promise.icon" class="size-4 text-accent-400" />
          {{ promise.title }}
        </li>
      </ul>
    </section>

    <!-- Tools -->
    <section id="tools" class="mx-auto max-w-6xl scroll-mt-20 px-6 py-16">
      <h2 class="text-2xl font-semibold text-white">Every tool you need</h2>
      <p class="mt-2 text-ink-400">
        Pick a file first — PDFFlow only offers the tools that fit what you uploaded.
      </p>

      <div v-for="category in categories" :key="category.key" class="mt-10">
        <h3 class="mb-3 text-sm font-medium uppercase tracking-wider text-ink-400">
          {{ category.label }}
        </h3>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <ToolCard
            v-for="operation in operations.filter((op) => op.category === category.key)"
            :key="operation.key"
            :operation="operation"
          />
        </div>
      </div>
    </section>

    <!-- Privacy -->
    <section id="privacy" class="mx-auto max-w-6xl scroll-mt-20 px-6 py-16">
      <div class="panel p-8 sm:p-12">
        <h2 class="text-2xl font-semibold text-white">What happens to your files</h2>
        <p class="mt-2 max-w-2xl text-ink-400">
          Most PDF sites ask you to trust a privacy policy. Here is the actual
          lifecycle instead.
        </p>

        <ol class="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <li v-for="(step, index) in [
            { title: 'Upload', body: 'Your file is written to a temporary directory under a random UUID name. Its original name is never used on disk.' },
            { title: 'Process', body: 'A background worker reads it, does the one operation you asked for, and writes the result.' },
            { title: 'Download', body: 'You fetch the result over a link tied to your job id. No index, no listing, no sharing.' },
            { title: 'Delete', body: 'Inputs are removed the moment the job ends; results within 30 minutes. A sweep runs every 5 minutes.' },
          ]" :key="step.title" class="space-y-2">
            <span class="flex size-8 items-center justify-center rounded-full bg-accent-500/15 text-sm font-semibold text-accent-400">
              {{ index + 1 }}
            </span>
            <h3 class="font-medium text-ink-200">{{ step.title }}</h3>
            <p class="text-sm leading-relaxed text-ink-400">{{ step.body }}</p>
          </li>
        </ol>
      </div>
    </section>
  </div>
</template>
