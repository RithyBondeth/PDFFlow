<script setup lang="ts">
defineProps<{ message: string }>()
defineEmits<{ dismiss: [] }>()
</script>

<template>
  <div
    role="alert"
    class="flex items-start gap-3 rounded-[10px] border border-alarm/35 bg-alarm-deep/25 px-4 py-3 text-left"
  >
    <UIcon name="i-lucide-alert-triangle" class="mt-0.5 size-5 shrink-0 text-alarm" />
    <p class="flex-1 text-sm text-paper">{{ message }}</p>
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
