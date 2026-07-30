<script setup lang="ts">
import type { Operation } from '~/types/api'

defineProps<{ operation: Operation; selected?: boolean }>()
defineEmits<{ select: [Operation] }>()

const ICONS: Record<string, string> = {
  merge: 'i-lucide-combine',
  split: 'i-lucide-scissors',
  extract_pages: 'i-lucide-file-output',
  rotate: 'i-lucide-rotate-cw',
  compress: 'i-lucide-minimize-2',
  organize: 'i-lucide-layout-grid',
  watermark: 'i-lucide-stamp',
  protect: 'i-lucide-lock',
  unlock: 'i-lucide-lock-open',
  extract_images: 'i-lucide-images',
  images_to_pdf: 'i-lucide-file-image',
  pdf_to_images: 'i-lucide-image-down',
  office_to_pdf: 'i-lucide-file-type-2',
}
</script>

<template>
  <button
    type="button"
    class="panel group flex w-full flex-col gap-2 p-4 text-left transition-all"
    :class="[
      selected
        ? 'border-accent-500 ring-1 ring-accent-500/40'
        : 'hover:-translate-y-0.5 hover:border-ink-700',
      !operation.implemented && 'cursor-not-allowed opacity-45 hover:translate-y-0',
    ]"
    :disabled="!operation.implemented"
    :aria-pressed="selected"
    @click="$emit('select', operation)"
  >
    <div class="flex items-center gap-2">
      <UIcon
        :name="ICONS[operation.key] ?? 'i-lucide-wand-2'"
        class="size-5 text-accent-400"
      />
      <span class="font-medium text-ink-200">{{ operation.name }}</span>
      <UBadge
        v-if="!operation.implemented"
        size="sm"
        color="neutral"
        variant="subtle"
        class="ml-auto"
      >
        Soon
      </UBadge>
    </div>
    <p class="text-sm leading-snug text-ink-400">
      {{ operation.description }}
    </p>
  </button>
</template>
