<script setup lang="ts">
defineProps<{ message: string }>()
defineEmits<{ dismiss: [] }>()
</script>

<template>
  <div
    role="alert"
    class="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-left"
  >
    <UIcon name="i-lucide-alert-circle" class="mt-0.5 size-5 shrink-0 text-red-400" />
    <p class="flex-1 text-sm text-red-200">{{ message }}</p>
    <UButton
      color="neutral"
      variant="ghost"
      size="xs"
      icon="i-lucide-x"
      aria-label="Dismiss"
      @click="$emit('dismiss')"
    />
  </div>
</template>
