<script setup lang="ts">
const api = useApi()
const workspace = useWorkspaceStore()
const job = useJobStream()

// The store is in-memory by design, so a hard reload has nothing to show.
onMounted(() => {
  if (!workspace.hasFiles) navigateTo('/')
})

const submitting = ref(false)
const now = useTimestamp({ interval: 1000 })
const timeLeft = computed(() => {
  void now.value // re-evaluate every tick
  return formatCountdown(workspace.expiresAt)
})

const canSubmit = computed(
  () =>
    workspace.selectedOperation !== null &&
    workspace.hasFiles &&
    !submitting.value &&
    !job.isTerminal.value &&
    !workspace.jobId,
)

async function run() {
  const operation = workspace.selectedOperation
  if (!operation) return

  submitting.value = true
  workspace.error = null
  try {
    const created = await api.createJob(
      operation.key,
      workspace.files.map((file) => file.id),
      { ...workspace.options },
    )
    workspace.jobId = created.id
    job.start(created.id)
  } catch (err) {
    workspace.error = (err as Error).message
  } finally {
    submitting.value = false
  }
}

function startOver() {
  job.stop()
  workspace.reset()
  navigateTo('/')
}

const savings = computed(() => {
  const result = job.state.result as Record<string, number>
  return typeof result.percentSaved === 'number' ? result : null
})
</script>

<template>
  <div class="mx-auto max-w-6xl px-6 py-12">
    <div class="mb-8 flex flex-wrap items-center gap-3">
      <h1 class="text-2xl font-semibold text-white">Your workspace</h1>
      <UBadge v-if="timeLeft" color="neutral" variant="subtle">
        <UIcon name="i-lucide-timer" class="mr-1 size-3.5" />
        Files deleted in {{ timeLeft }}
      </UBadge>
      <UButton
        class="ml-auto"
        variant="ghost"
        color="neutral"
        icon="i-lucide-rotate-ccw"
        @click="startOver"
      >
        Start over
      </UButton>
    </div>

    <ErrorMessage
      v-if="workspace.error"
      class="mb-6"
      :message="workspace.error"
      @dismiss="workspace.error = null"
    />

    <div class="grid gap-6 lg:grid-cols-[320px_1fr]">
      <!-- Files -->
      <aside class="space-y-3">
        <div class="flex items-baseline justify-between">
          <h2 class="text-sm font-medium uppercase tracking-wider text-ink-400">
            Files ({{ workspace.files.length }})
          </h2>
          <span class="text-xs text-ink-400">{{ formatBytes(workspace.totalSize) }}</span>
        </div>

        <FileList
          :files="workspace.files"
          :reorderable="workspace.selectedOperation?.multiFile ?? false"
          @remove="workspace.removeFile"
          @reorder="workspace.reorder"
        />

        <p
          v-if="workspace.selectedOperation?.multiFile"
          class="text-xs text-ink-400"
        >
          Drag to set the order files are combined in.
        </p>
      </aside>

      <!-- Tool + job -->
      <section class="space-y-6">
        <template v-if="!workspace.jobId">
          <div>
            <h2 class="mb-3 text-sm font-medium uppercase tracking-wider text-ink-400">
              Choose a tool
            </h2>
            <div class="grid gap-3 sm:grid-cols-2">
              <ToolCard
                v-for="operation in workspace.operations"
                :key="operation.key"
                :operation="operation"
                :selected="workspace.selectedOperation?.key === operation.key"
                @select="workspace.selectOperation"
              />
            </div>
          </div>

          <ToolOptions
            v-if="workspace.selectedOperation"
            v-model="workspace.options"
            :operation="workspace.selectedOperation"
          />

          <UButton
            size="xl"
            color="primary"
            block
            :loading="submitting"
            :disabled="!canSubmit"
            icon="i-lucide-play"
            @click="run"
          >
            {{ workspace.selectedOperation ? `Run ${workspace.selectedOperation.name}` : 'Select a tool to continue' }}
          </UButton>
        </template>

        <!-- Job progress -->
        <template v-else>
          <JobStatus
            :status="job.state.status"
            :progress="job.state.progress"
            :label="job.label.value"
            :error-message="job.state.errorMessage"
          />

          <div v-if="job.state.status === 'completed'" class="panel space-y-4 p-6">
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-file-check-2" class="size-8 text-green-400" />
              <div class="min-w-0">
                <p class="truncate font-medium text-ink-200">
                  {{ job.state.outputFilename }}
                </p>
                <p class="text-sm text-ink-400">
                  {{ formatBytes(job.state.outputSize ?? 0) }}
                  <template v-if="savings">
                    · {{ savings.percentSaved }}% smaller than
                    {{ formatBytes(savings.originalSize) }}
                  </template>
                </p>
              </div>
            </div>

            <UButton
              :to="api.downloadUrl(workspace.jobId)"
              external
              download
              size="xl"
              color="primary"
              block
              icon="i-lucide-download"
            >
              Download result
            </UButton>

            <p class="text-center text-xs text-ink-400">
              This link stops working in {{ timeLeft }}, when the file is deleted.
            </p>
          </div>

          <UButton
            v-if="job.isTerminal.value"
            variant="ghost"
            color="neutral"
            block
            icon="i-lucide-plus"
            @click="startOver"
          >
            Process another file
          </UButton>
        </template>
      </section>
    </div>
  </div>
</template>
