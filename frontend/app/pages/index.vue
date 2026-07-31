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
  { key: 'organize', label: 'Organise', blurb: 'Change what the document contains' },
  { key: 'optimize', label: 'Optimise', blurb: 'Make it smaller without wrecking it' },
  { key: 'convert', label: 'Convert', blurb: 'Move between PDF and other formats' },
  { key: 'security', label: 'Security', blurb: 'Add or remove a password' },
  { key: 'edit', label: 'Edit', blurb: 'Mark up the pages themselves' },
] as const

const readyCount = computed(() => operations.value.filter((op) => op.implemented).length)

function toolsIn(key: string) {
  return operations.value.filter((op) => op.category === key)
}

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
  { icon: 'i-lucide-user-x', label: 'No account' },
  { icon: 'i-lucide-eye-off', label: 'No tracking' },
  { icon: 'i-lucide-timer', label: 'Gone in 30 min' },
]

/**
 * The lifecycle of one file, keyed by when each thing happens. The times are
 * the organising information here — far more use to someone deciding whether
 * to trust the page than a decorative 01/02/03 would be.
 */
const lifecycle = [
  {
    at: 't + 0s',
    title: 'Arrives',
    body: 'Written to a temporary directory under a random UUID. The name you gave it is never used on disk.',
  },
  {
    at: 't + ~2s',
    title: 'Processed',
    body: 'A background worker reads it, does the one operation you asked for, and writes the result.',
  },
  {
    at: 'on request',
    title: 'Downloaded',
    body: 'Fetched over a link tied to your job id. There is no index, no listing and no sharing.',
  },
  {
    at: 't + 30 min',
    title: 'Gone',
    body: 'Inputs are removed the moment the job ends, results within 30 minutes. A sweep runs every 5 minutes.',
  },
]
</script>

<template>
  <div>
    <!-- ==================== Hero ==================== -->
    <section id="upload" class="relative scroll-mt-16 px-5 pb-14 pt-12 sm:px-6 sm:pt-16">
      <div class="mx-auto max-w-6xl">
        <!-- Claim beside evidence: the headline makes the promise, the panel
             shows it happening. They are near enough in height to sit as a pair
             without either column trailing off into empty space. -->
        <div class="grid items-center gap-10 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
          <div>
            <p class="enter-rise eyebrow">{{ readyCount }} tools ready · no signup</p>

            <h1
              class="enter-rise font-display mt-5 text-[2.5rem] font-bold leading-[1] tracking-[-0.025em] text-ink sm:text-[3.25rem] lg:text-[3.4rem]"
              style="--enter-delay: 0.08s"
            >
              PDF tools that<br>
              <span class="mark">forget you were here.</span>
            </h1>

            <p
              class="enter-rise mt-6 max-w-lg text-pretty text-lg leading-relaxed text-ink-muted"
              style="--enter-delay: 0.16s"
            >
              Merge, split, compress and convert documents in seconds. No email, no
              password, no cookie banner — and every file you send is deleted
              within half an hour of arriving.
            </p>
          </div>

          <DevelopingPanel class="enter-drift" style="--enter-delay: 0.2s" />
        </div>

        <!-- Full width, because the drop target should be the largest thing on
             the page once you have read the headline. -->
        <div class="enter-rise mt-10" style="--enter-delay: 0.26s">
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
          class="enter-rise mt-6 flex flex-wrap items-center justify-center gap-x-7 gap-y-2.5"
          style="--enter-delay: 0.34s"
        >
          <li
            v-for="promise in promises"
            :key="promise.label"
            class="font-data flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-ink-faint"
          >
            <UIcon :name="promise.icon" class="size-3.5 text-accent-500" />
            {{ promise.label }}
          </li>
        </ul>
      </div>
    </section>

    <!-- ==================== Tools ==================== -->
    <section id="tools" class="mx-auto max-w-6xl scroll-mt-16 px-5 py-16 sm:px-6">
      <div class="reveal max-w-2xl">
        <p class="eyebrow">The toolbox</p>
        <h2
          class="font-display mt-4 text-balance text-3xl font-bold tracking-[-0.02em] text-ink sm:text-[2.5rem]"
        >
          Everything you'd otherwise install software for
        </h2>
        <p class="mt-3 text-pretty text-ink-muted">
          Add your file first and PDFFlow shows only the tools that fit it — a
          password can't be stripped off a JPEG, so it won't offer to.
        </p>
      </div>

      <div v-for="category in categories" :key="category.key" class="mt-12">
        <div class="reveal mb-4 flex items-baseline gap-4">
          <h3 class="font-data text-xs uppercase tracking-[0.2em] text-ink">
            {{ category.label }}
          </h3>
          <span class="hidden text-sm text-ink-faint sm:inline">{{ category.blurb }}</span>
          <span class="h-px flex-1 bg-hairline" aria-hidden="true" />
          <span class="font-data text-xs tabular-nums text-ink-faint">
            {{ toolsIn(category.key).length }}
          </span>
        </div>

        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <ToolCard
            v-for="operation in toolsIn(category.key)"
            :key="operation.key"
            :operation="operation"
          />
        </div>
      </div>
    </section>

    <!-- ==================== Lifecycle ==================== -->
    <section id="lifecycle" class="mx-auto max-w-6xl scroll-mt-16 px-5 py-20 sm:px-6">
      <div class="panel reveal overflow-hidden p-6 sm:p-10">
        <div class="max-w-2xl">
          <p class="eyebrow">What happens to your file</p>
          <h2
            class="font-display mt-4 text-balance text-3xl font-bold tracking-[-0.02em] text-ink sm:text-[2.5rem]"
          >
            The whole life of an upload
          </h2>
          <p class="mt-3 text-pretty text-ink-muted">
            Most PDF sites ask you to trust a privacy policy. Here is the actual
            sequence instead, with the times it happens at.
          </p>
        </div>

        <!-- The rail runs the width of the section and each step hangs off it on
             its own tick, so the same fuse that measures a real job in the
             workspace is what this sequence is pinned to. Below sm the rail is
             dropped and each step keeps a plain left rule instead. -->
        <div class="fuse mt-10 hidden sm:block" style="--burn: 100%" aria-hidden="true" />

        <ol class="mt-6 grid gap-8 sm:mt-0 sm:grid-cols-2 sm:gap-x-6 lg:grid-cols-4">
          <li
            v-for="step in lifecycle"
            :key="step.title"
            class="relative border-l border-hairline pl-4 sm:border-l-0 sm:pl-0 sm:pt-7"
          >
            <span
              class="absolute left-0 top-0 hidden h-4 w-px bg-hairline-strong sm:block"
              aria-hidden="true"
            />
            <p class="font-data text-xs tabular-nums text-accent-ink">{{ step.at }}</p>
            <h3 class="mt-2 font-medium text-ink">{{ step.title }}</h3>
            <p class="mt-1.5 text-sm leading-relaxed text-ink-muted">{{ step.body }}</p>
          </li>
        </ol>
      </div>
    </section>
  </div>
</template>
