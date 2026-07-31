<script setup lang="ts">
const props = defineProps<{
  status: string
  progress: number
  label: string
  errorMessage?: string | null
}>()

const tone = computed(() => {
  if (props.status === 'failed' || props.status === 'expired') return 'error'
  if (props.status === 'completed') return 'success'
  return 'active'
})
</script>

<template>
  <div class="panel space-y-4 p-5">
    <div class="flex items-center gap-3">
      <UIcon
        v-if="tone === 'active'"
        name="i-lucide-loader-2"
        class="size-5 animate-spin text-accent-ink"
      />
      <UIcon v-else-if="tone === 'success'" name="i-lucide-check" class="size-5 text-good" />
      <UIcon v-else name="i-lucide-alert-triangle" class="size-5 text-bad" />

      <p class="flex-1 text-sm font-medium text-ink">
        {{ errorMessage || label }}
      </p>
      <span class="font-data text-xs tabular-nums text-ink-muted">{{ progress }}%</span>
    </div>

    <!-- Same rail as everywhere else, recoloured by outcome: the safelight
         while it runs, good once it is a real result, bad if it isn't. -->
    <div
      class="fuse"
      :class="{
        'fuse-good': tone === 'success',
        'fuse-bad': tone === 'error',
      }"
      :style="{ '--burn': `${Math.max(progress, 3)}%` }"
      role="progressbar"
      :aria-valuenow="progress"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="label"
    />
  </div>
</template>
