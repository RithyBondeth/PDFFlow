<script setup lang="ts">
defineProps<{
  uploading: boolean
  progress: number
  error: string | null
}>()

const emit = defineEmits<{
  files: [File[]]
  error: [string]
  dismiss: []
}>()
</script>

<template>
  <div class="space-y-3">
    <ErrorMessage v-if="error" :message="error" @dismiss="emit('dismiss')" />

    <DropZone
      v-if="!uploading"
      @files="emit('files', $event)"
      @error="emit('error', $event)"
    />

    <!-- Same footprint and same arrangement as the drop zone, so the panel does
         not jump when the upload starts. -->
    <div v-else class="panel px-5 py-8 sm:px-7 sm:py-6">
      <div class="flex flex-col items-center gap-5 sm:flex-row sm:gap-6">
        <div
          class="flex size-12 shrink-0 items-center justify-center rounded-full border border-accent-500/35 bg-accent-500/10 text-accent-300"
        >
          <UIcon name="i-lucide-loader-2" class="size-5 animate-spin" />
        </div>

        <div class="w-full space-y-2.5 sm:flex-1">
          <div class="flex items-baseline justify-between gap-4">
            <p class="font-display text-xl font-bold tracking-tight text-paper">
              Sending your file
            </p>
            <p class="font-data text-xs tabular-nums text-accent-300">{{ progress }}%</p>
          </div>
          <div
            class="fuse"
            :style="{ '--burn': `${Math.max(progress, 2)}%` }"
            role="progressbar"
            :aria-valuenow="progress"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-label="Upload progress"
          />
        </div>
      </div>
    </div>
  </div>
</template>
