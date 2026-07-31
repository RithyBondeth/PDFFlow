<script setup lang="ts">
import type { Operation } from '~/types/api'

const props = defineProps<{ operation: Operation; selected?: boolean }>()
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

const icon = computed(() => ICONS[props.operation.key] ?? 'i-lucide-wand-2')
</script>

<template>
  <button
    type="button"
    class="panel reveal group flex w-full flex-col gap-2.5 p-4 text-left transition-colors duration-200"
    :class="[
      selected ? 'border-accent-500 bg-accent-500/[0.04]' : 'hover:border-hairline-strong',
      operation.implemented ? '' : 'cursor-not-allowed opacity-50',
    ]"
    :disabled="!operation.implemented"
    :aria-pressed="selected"
    @click="$emit('select', operation)"
  >
    <div class="flex items-center gap-2.5">
      <!-- Only the chosen tool gets the accent fill. Everything else is a hairline
           box, so a grid of twelve cards has exactly one focal point. -->
      <span
        class="flex size-8 shrink-0 items-center justify-center rounded-[5px] border transition-colors duration-200"
        :class="
          selected
            ? 'border-transparent bg-accent-500 text-white'
            : 'border-hairline text-ink-muted group-hover:border-hairline-strong group-hover:text-ink'
        "
      >
        <UIcon :name="icon" class="size-4" />
      </span>
      <span class="font-medium text-ink">{{ operation.name }}</span>
      <span
        v-if="!operation.implemented"
        class="font-data ml-auto text-[10px] uppercase tracking-[0.14em] text-ink-faint"
      >
        Soon
      </span>
      <UIcon
        v-else-if="selected"
        name="i-lucide-check"
        class="ml-auto size-4 text-accent-ink"
      />
    </div>
    <p class="text-sm leading-snug text-ink-muted">
      {{ operation.description }}
    </p>
  </button>
</template>
