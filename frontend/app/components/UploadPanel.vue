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

    <div v-else class="panel space-y-4 px-8 py-14">
      <p class="text-lg font-medium text-ink-200">Uploading your file…</p>
      <div class="h-1.5 overflow-hidden rounded-full bg-ink-800">
        <div
          class="h-full rounded-full bg-accent-500 transition-[width] duration-200"
          :style="{ width: `${Math.max(progress, 3)}%` }"
        />
      </div>
      <p class="text-sm tabular-nums text-ink-400">{{ progress }}%</p>
    </div>
  </div>
</template>
