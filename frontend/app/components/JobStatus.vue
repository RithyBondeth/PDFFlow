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
        class="size-5 animate-spin text-accent-300"
      />
      <UIcon v-else-if="tone === 'success'" name="i-lucide-check" class="size-5 text-fixer" />
      <UIcon v-else name="i-lucide-alert-triangle" class="size-5 text-alarm" />

      <p class="flex-1 text-sm font-medium text-paper">
        {{ errorMessage || label }}
      </p>
      <span class="font-data text-xs tabular-nums text-paper-dim">{{ progress }}%</span>
    </div>

    <!-- Same rail as everywhere else, recoloured by outcome: the safelight
         while it runs, fixer once it is a real result, alarm if it isn't. -->
    <div
      class="fuse"
      :class="{
        'fuse-success': tone === 'success',
        'fuse-error': tone === 'error',
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
