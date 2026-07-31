<script setup lang="ts">
import type { Operation } from '~/types/api'
import { fallbackOperations } from '~/data/operationCatalog'

const api = useApi()
const workspace = useWorkspaceStore()

const config = useRuntimeConfig()
const siteUrl = String(config.public.siteUrl).replace(/\/$/, '')

useSeo({
  title: 'PDFFlow — Fast, Private PDF Tools. No Signup Required.',
  description:
    'Merge, split, compress, rotate and extract pages from PDFs in seconds. No account, no tracking, and every file is deleted automatically within 30 minutes.',
})

// Search engines render tool sites from structured data as often as from the
// copy. WebApplication is the accurate type — it runs in the browser, it is
// free, and it needs no account, all of which are things worth stating in a
// form a crawler can read directly.
useHead({
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebApplication',
        name: 'PDFFlow',
        url: `${siteUrl}/`,
        description:
          'Fast, private PDF tools. Merge, split, compress, rotate and extract pages with no account and no permanent storage.',
        applicationCategory: 'UtilitiesApplication',
        operatingSystem: 'Any',
        browserRequirements: 'Requires JavaScript',
        isAccessibleForFree: true,
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'USD',
        },
        featureList: [
          'Merge PDF',
          'Split PDF',
          'Extract pages',
          'Rotate PDF',
          'Organize PDF pages',
          'Compress PDF',
        ],
      }),
    },
  ],
})

const uploading = ref(false)
const uploadProgress = ref(0)
const error = ref<string | null>(null)

const { data: operations } = await useAsyncData<Operation[]>(
  'operations',
  async () => {
    try {
      const catalog = await api.operations()
      return catalog.length ? catalog : fallbackOperations
    } catch {
      return fallbackOperations
    }
  },
  { default: () => fallbackOperations },
)

const categories = [
  { key: 'organize', label: 'Organise', blurb: 'Change what the document contains' },
  { key: 'optimize', label: 'Optimise', blurb: 'Make it smaller without wrecking it' },
  { key: 'convert', label: 'Convert', blurb: 'Move between PDF and other formats' },
  { key: 'security', label: 'Security', blurb: 'Add or remove a password' },
  { key: 'edit', label: 'Edit', blurb: 'Mark up the pages themselves' },
] as const

const readyCount = computed(() => operations.value.filter((op) => op.implemented).length)
const plannedCount = computed(() => operations.value.length - readyCount.value)

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
    icon: 'i-lucide-cloud-upload',
    at: 't + 0s',
    title: 'Upload',
    body: 'Written to a temporary directory under a random UUID. The name you gave it is never used on disk.',
    mockTitle: 'quarterly-report.pdf',
    mockMeta: '12.4 MB · temporary',
  },
  {
    icon: 'i-lucide-wand-sparkles',
    at: 't + ~2s',
    title: 'Choose a tool',
    body: 'A background worker reads it, does the one operation you asked for, and writes the result.',
    mockTitle: 'Compress PDF',
    mockMeta: 'Processing securely',
  },
  {
    icon: 'i-lucide-download',
    at: 'on request',
    title: 'Download',
    body: 'Fetched over a link tied to your job id. There is no index, no listing and no sharing.',
    mockTitle: 'quarterly-report-compressed.pdf',
    mockMeta: '3.9 MB · ready',
  },
  {
    icon: 'i-lucide-trash-2',
    at: 't + 30 min',
    title: 'Auto-delete',
    body: 'Inputs are removed the moment the job ends, results within 30 minutes. A sweep runs every 5 minutes.',
    mockTitle: 'Files deleted',
    mockMeta: 'Nothing left behind',
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
              <span class="mark mark-draw" style="--enter-delay: 0.45s">forget you were here.</span>
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
      <div class="reveal max-w-3xl">
        <p class="eyebrow">The toolbox</p>
        <h2
          class="font-display mt-4 text-balance text-3xl font-bold tracking-[-0.02em] text-ink sm:text-[2.5rem]"
        >
          Everything you'd otherwise install software for
        </h2>
        <p class="mt-3 max-w-2xl text-pretty text-ink-muted">
          Browse all {{ operations.length }} tools below. {{ readyCount }} work today
          and {{ plannedCount }} are clearly marked as planned, with the accepted file
          types, number of files and output format shown on every card.
        </p>

        <div class="mt-5 flex flex-wrap gap-2">
          <span class="font-data rounded-full border border-good/30 bg-good/10 px-3 py-1 text-[10px] uppercase tracking-[0.12em] text-good">
            {{ readyCount }} ready now
          </span>
          <span class="font-data rounded-full border border-hairline px-3 py-1 text-[10px] uppercase tracking-[0.12em] text-ink-faint">
            {{ plannedCount }} on the roadmap
          </span>
        </div>
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
            v-for="(operation, index) in toolsIn(category.key)"
            :key="operation.key"
            :operation="operation"
            :column="index % 3"
          />
        </div>
      </div>
    </section>

    <!-- ==================== Lifecycle ==================== -->
    <section id="lifecycle" class="mx-auto max-w-6xl scroll-mt-16 px-5 py-20 sm:px-6">
      <div class="panel reveal overflow-hidden p-6 sm:p-10">
        <div class="max-w-3xl">
          <p class="eyebrow">How it works</p>
          <h2
            class="font-display mt-4 text-balance text-3xl font-bold tracking-[-0.02em] text-ink sm:text-[2.5rem]"
          >
            From upload to automatic deletion
          </h2>
          <p class="mt-3 text-pretty text-ink-muted">
            Four small steps, shown exactly as they happen. Your original file is
            removed after processing and the result expires within 30 minutes.
          </p>
        </div>

        <!-- The rail runs the width of the section and each step hangs off it on
             its own tick, so the same fuse that measures a real job in the
             workspace is what this sequence is pinned to. Below sm the rail is
             dropped and each step keeps a plain left rule instead. -->
        <div class="fuse mt-10 hidden sm:block" style="--burn: 100%" aria-hidden="true" />

        <ol class="mt-6 grid gap-4 sm:mt-0 sm:grid-cols-2 lg:grid-cols-4">
          <li
            v-for="step in lifecycle"
            :key="step.title"
            class="relative flex flex-col rounded-md border border-hairline bg-raised/60 p-4 sm:mt-7"
          >
            <div class="flex items-center justify-between gap-3">
              <span class="flex size-9 items-center justify-center rounded-md bg-accent-500/10 text-accent-ink">
                <UIcon :name="step.icon" class="size-4.5" />
              </span>
              <p class="font-data text-[10px] tabular-nums uppercase tracking-[0.1em] text-accent-ink">
                {{ step.at }}
              </p>
            </div>

            <h3 class="mt-4 font-display text-lg font-semibold text-ink">{{ step.title }}</h3>
            <p class="mt-1.5 text-sm leading-relaxed text-ink-muted">{{ step.body }}</p>

            <div class="trough mt-5 flex items-center gap-2.5 p-2.5" aria-hidden="true">
              <span class="flex size-7 shrink-0 items-center justify-center rounded bg-accent-500 text-white">
                <UIcon :name="step.icon" class="size-3.5" />
              </span>
              <span class="min-w-0">
                <span class="block truncate text-xs font-medium text-ink">{{ step.mockTitle }}</span>
                <span class="font-data block truncate text-[9px] uppercase tracking-[0.08em] text-ink-faint">
                  {{ step.mockMeta }}
                </span>
              </span>
            </div>
          </li>
        </ol>
      </div>
    </section>

    <!-- ==================== Community support ==================== -->
    <section id="support" class="mx-auto max-w-6xl scroll-mt-16 px-5 pb-20 sm:px-6">
      <div class="panel reveal overflow-hidden">
        <div class="grid lg:grid-cols-[1fr_0.72fr]">
          <div class="p-6 sm:p-10 lg:p-12">
            <div class="flex items-center gap-3">
              <span class="flex size-10 items-center justify-center rounded-md bg-accent-500/10 text-accent-ink">
                <UIcon name="i-lucide-heart-handshake" class="size-5" />
              </span>
              <p class="eyebrow">Made in the open</p>
            </div>

            <h2
              class="font-display mt-6 max-w-xl text-balance text-3xl font-bold tracking-[-0.02em] text-ink sm:text-[2.5rem]"
            >
              Help keep PDFFlow<br>
              <span class="mark">free and growing.</span>
            </h2>
            <p class="mt-4 max-w-xl text-pretty leading-relaxed text-ink-muted">
              If PDFFlow saved you a little time, a GitHub star helps more people
              find it. Follow along to see new tools as they ship and help shape
              what gets built next.
            </p>

            <div class="mt-8 flex flex-col gap-3 sm:flex-row">
              <UButton
                to="https://github.com/RithyBondeth/PDFFlow"
                target="_blank"
                rel="noopener noreferrer"
                color="primary"
                size="lg"
                icon="i-lucide-star"
                trailing-icon="i-lucide-external-link"
              >
                Star on GitHub
              </UButton>
              <UButton
                to="https://github.com/RithyBondeth"
                target="_blank"
                rel="noopener noreferrer"
                color="neutral"
                variant="outline"
                size="lg"
                icon="i-lucide-github"
              >
                Follow @RithyBondeth
              </UButton>
            </div>
          </div>

          <div class="border-t border-hairline bg-sunken p-6 sm:p-10 lg:border-l lg:border-t-0 lg:p-12">
            <div class="flex h-full flex-col justify-between gap-10">
              <div>
                <div class="flex items-center justify-between gap-4">
                  <span class="flex size-11 items-center justify-center rounded-md bg-ink text-canvas">
                    <UIcon name="i-lucide-github" class="size-5.5" />
                  </span>
                  <span class="font-data rounded-full border border-good/30 bg-good/10 px-3 py-1 text-[10px] uppercase tracking-[0.12em] text-good">
                    Open source
                  </span>
                </div>

                <p class="font-data mt-8 text-[11px] uppercase tracking-[0.14em] text-ink-faint">
                  github.com
                </p>
                <p class="mt-1 font-display text-xl font-bold text-ink">
                  RithyBondeth / PDFFlow
                </p>
                <p class="mt-3 text-sm leading-relaxed text-ink-muted">
                  Every star is a small signal that this project is useful — and
                  a lovely bit of fuel for the next release.
                </p>
              </div>

              <div class="flex items-center gap-3 border-t border-hairline pt-5">
                <span class="flex size-8 items-center justify-center rounded-full bg-accent-500/10 text-accent-ink">
                  <UIcon name="i-lucide-sparkles" class="size-4" />
                </span>
                <p class="font-data text-[11px] uppercase tracking-[0.1em] text-ink-faint">
                  One click · a big encouragement
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
