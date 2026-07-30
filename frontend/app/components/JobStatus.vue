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
  <div class="panel space-y-3 p-5">
    <div class="flex items-center gap-3">
      <UIcon
        v-if="tone === 'active'"
        name="i-lucide-loader-2"
        class="size-5 animate-spin text-accent-600"
      />
      <UIcon
        v-else-if="tone === 'success'"
        name="i-lucide-check-circle-2"
        class="size-5 text-green-600"
      />
      <UIcon v-else name="i-lucide-alert-circle" class="size-5 text-red-600" />

      <p class="flex-1 text-sm font-medium text-ink-200">
        {{ errorMessage || label }}
      </p>
      <span class="text-sm tabular-nums text-ink-400">{{ progress }}%</span>
    </div>

    <div
      class="h-1.5 w-full overflow-hidden rounded-full bg-ink-800"
      role="progressbar"
      :aria-valuenow="progress"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="label"
    >
      <div
        class="h-full rounded-full transition-[width] duration-500 ease-out"
        :class="{
          'bg-accent-500': tone === 'active',
          'bg-green-500': tone === 'success',
          'bg-red-500': tone === 'error',
        }"
        :style="{ width: `${Math.max(progress, 4)}%` }"
      />
    </div>
  </div>
</template>
