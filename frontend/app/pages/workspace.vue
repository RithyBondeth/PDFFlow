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

// The same rail the landing page uses to state the 30-minute promise, here
// wired to the actual expiry. This is the one that is literally true.
const burn = computed(() => {
  void now.value
  return burnPercent(workspace.expiresAt)
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

// The heading is a signpost, so it says where you actually are rather than
// telling someone to pick a tool while their finished file sits below it.
const heading = computed(() => {
  if (!workspace.jobId) return 'Pick what to do'
  if (job.state.status === 'completed') return 'Your file is ready'
  if (job.isTerminal.value) return 'That did not work'
  return 'Working on it'
})

const savings = computed(() => {
  const result = job.state.result as Record<string, number | boolean>
  return typeof result.percentSaved === 'number'
    ? (result as { percentSaved: number; originalSize: number; alreadyOptimized: boolean })
    : null
})
</script>

<template>
  <div class="mx-auto max-w-6xl px-5 py-10 sm:px-6 sm:py-12">
    <div class="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="eyebrow">Your session</p>
        <h1
          class="font-display mt-3 text-3xl font-extrabold tracking-[-0.02em] text-paper sm:text-4xl"
        >
          {{ heading }}
        </h1>
      </div>
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-lucide-rotate-ccw"
        class="text-paper-dim hover:text-paper"
        @click="startOver"
      >
        Start over
      </UButton>
    </div>

    <!-- The countdown gets its own full-width rail at the top of the page: it
         applies to everything below it, and it is the one number a visitor was
         promised on the way in. -->
    <div v-if="timeLeft" class="panel mb-6 px-5 py-4">
      <TimeFuse :burn="burn" label="Everything here is deleted in" :value="timeLeft" />
    </div>

    <ErrorMessage
      v-if="workspace.error"
      class="mb-6"
      :message="workspace.error"
      @dismiss="workspace.error = null"
    />

    <div class="grid gap-6 lg:grid-cols-[300px_1fr]">
      <!-- Files -->
      <aside class="space-y-3">
        <div class="flex items-baseline gap-3">
          <h2 class="font-data text-xs uppercase tracking-[0.2em] text-paper">
            Files
          </h2>
          <span class="h-px flex-1 bg-line" aria-hidden="true" />
          <span class="font-data text-xs tabular-nums text-paper-faint">
            {{ formatBytes(workspace.totalSize) }}
          </span>
        </div>

        <FileList
          :files="workspace.files"
          :reorderable="workspace.selectedOperation?.multiFile ?? false"
          @remove="workspace.removeFile"
          @reorder="workspace.reorder"
        />

        <p v-if="workspace.selectedOperation?.multiFile" class="text-xs text-paper-faint">
          Drag to set the order the files are combined in.
        </p>
      </aside>

      <!-- Tool + job -->
      <section class="space-y-6">
        <template v-if="!workspace.jobId">
          <div>
            <div class="mb-4 flex items-baseline gap-3">
              <h2 class="font-data text-xs uppercase tracking-[0.2em] text-paper">
                Tools that fit these files
              </h2>
              <span class="h-px flex-1 bg-line" aria-hidden="true" />
            </div>
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

          <!-- Only a runnable action wears the safelight. Until a tool is
               picked this is an outline, so nothing on the page looks pressable
               that isn't. -->
          <UButton
            size="xl"
            :color="canSubmit ? 'primary' : 'neutral'"
            :variant="canSubmit ? 'solid' : 'outline'"
            block
            :loading="submitting"
            :disabled="!canSubmit"
            icon="i-lucide-play"
            :class="
              canSubmit
                ? 'shadow-[0_0_32px_-12px_oklch(0.772_0.155_76/0.55)] hover:shadow-[0_0_40px_-10px_oklch(0.772_0.155_76/0.7)]'
                : ''
            "
            @click="run"
          >
            {{ workspace.selectedOperation ? `Run ${workspace.selectedOperation.name}` : 'Pick a tool to continue' }}
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

          <!-- A finished result is the one thing on this page that is allowed to
               look permanent, so it gets the fixer edge. -->
          <div
            v-if="job.state.status === 'completed'"
            class="panel space-y-5 border-fixer/30 p-5 sm:p-6"
          >
            <div class="flex items-center gap-3">
              <span
                class="flex size-10 shrink-0 items-center justify-center rounded-lg border border-fixer/35 bg-fixer/10 text-fixer"
              >
                <UIcon name="i-lucide-file-check-2" class="size-5" />
              </span>
              <div class="min-w-0">
                <p class="truncate font-medium text-paper">
                  {{ job.state.outputFilename }}
                </p>
                <p class="font-data text-xs tabular-nums text-paper-dim">
                  {{ formatBytes(job.state.outputSize ?? 0) }}
                  <template v-if="savings?.alreadyOptimized">
                    · already optimised, no reduction possible
                  </template>
                  <template v-else-if="savings">
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
              class="shadow-[0_0_32px_-12px_oklch(0.772_0.155_76/0.55)] hover:shadow-[0_0_40px_-10px_oklch(0.772_0.155_76/0.7)]"
            >
              Download result
            </UButton>

            <p class="text-center text-xs text-paper-faint">
              This link stops working in {{ timeLeft }}, when the file is deleted.
            </p>
          </div>

          <UButton
            v-if="job.isTerminal.value"
            variant="ghost"
            color="neutral"
            block
            icon="i-lucide-plus"
            class="text-paper-dim hover:text-paper"
            @click="startOver"
          >
            Work on another file
          </UButton>
        </template>
      </section>
    </div>
  </div>
</template>
