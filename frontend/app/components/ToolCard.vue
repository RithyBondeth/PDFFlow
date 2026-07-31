<script setup lang="ts">
import type { Operation } from '~/types/api'

const props = defineProps<{ operation: Operation; selected?: boolean }>()
defineEmits<{ select: [Operation] }>()

const { track } = useSpotlight()

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
    class="panel spotlight reveal group flex w-full flex-col gap-2.5 p-4 text-left transition duration-200"
    :class="[
      selected
        ? 'border-accent-400/70 shadow-[0_0_0_1px_oklch(0.822_0.145_79/0.35),0_0_44px_-14px_oklch(0.772_0.155_76/0.6)]'
        : 'hover:border-line-lit',
      operation.implemented
        ? 'hover:-translate-y-0.5'
        : 'cursor-not-allowed opacity-40',
    ]"
    :disabled="!operation.implemented"
    :aria-pressed="selected"
    @pointermove="track"
    @click="$emit('select', operation)"
  >
    <div class="flex items-center gap-2.5">
      <span
        class="flex size-8 shrink-0 items-center justify-center rounded-lg border transition-colors duration-200"
        :class="
          selected
            ? 'border-accent-400/60 bg-accent-500/15 text-accent-300'
            : 'border-line bg-canvas/60 text-paper-dim group-hover:border-accent-500/40 group-hover:text-accent-300'
        "
      >
        <UIcon :name="icon" class="size-4" />
      </span>
      <span class="font-medium text-paper">{{ operation.name }}</span>
      <span
        v-if="!operation.implemented"
        class="font-data ml-auto text-[10px] uppercase tracking-[0.14em] text-paper-faint"
      >
        Soon
      </span>
      <UIcon
        v-else-if="selected"
        name="i-lucide-check"
        class="ml-auto size-4 text-accent-300"
      />
    </div>
    <p class="text-sm leading-snug text-paper-dim">
      {{ operation.description }}
    </p>
  </button>
</template>
