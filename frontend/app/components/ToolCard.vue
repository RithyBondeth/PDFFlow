<script setup lang="ts">
import type { Operation } from '~/types/api'

const props = defineProps<{ operation: Operation; selected?: boolean; index?: number }>()
defineEmits<{ select: [Operation] }>()

const indexLabel = computed(() =>
  props.index ? String(props.index).padStart(2, '0') : null,
)

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
    class="panel reveal group flex w-full flex-col gap-2 p-4 text-left transition duration-200"
    :class="[
      selected
        ? 'border-accent-500 ring-1 ring-accent-500/40'
        : 'hover:border-ink-700',
      operation.implemented
        ? 'hover:-translate-y-1 hover:shadow-lg hover:shadow-ink-950/5 active:translate-y-0'
        : 'cursor-not-allowed opacity-45',
    ]"
    :disabled="!operation.implemented"
    :aria-pressed="selected"
    @click="$emit('select', operation)"
  >
    <div class="flex items-center gap-2">
      <span v-if="indexLabel" class="font-mono text-xs text-ink-700">{{ indexLabel }}</span>
      <UIcon
        :name="ICONS[operation.key] ?? 'i-lucide-wand-2'"
        class="size-5 text-accent-600 transition-transform duration-200 group-hover:scale-110"
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
