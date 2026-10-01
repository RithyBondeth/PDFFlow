<script setup lang="ts">
import type { PageRotation } from '~/utils/pageOrganizer'

/**
 * One page preview inside an organiser card. Asks for its image only once it
 * is near the viewport, so a long document renders as you scroll rather than
 * all at once.
 */
const props = defineProps<{
  source: number
  rotation: PageRotation
  src: string | undefined
}>()

const emit = defineEmits<{ visible: [page: number] }>()

const root = ref<HTMLElement>()

onMounted(() => {
  if (props.src) return
  if (typeof IntersectionObserver === 'undefined') {
    emit('visible', props.source)
    return
  }
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        emit('visible', props.source)
        observer.disconnect()
      }
    },
    { rootMargin: '300px 0px' },
  )
  if (root.value) observer.observe(root.value)
  onBeforeUnmount(() => observer.disconnect())
})

// The preview box is 3:4. A quarter turn swaps the content's width and
// height, so the rotated layer is sized 4:3 first; once turned it fills the
// same box instead of overflowing it.
const sideways = computed(() => props.rotation === 90 || props.rotation === 270)
</script>

<template>
  <div
    ref="root"
    class="relative aspect-[3/4] overflow-hidden rounded border border-hairline bg-surface"
  >
    <div
      class="absolute left-1/2 top-1/2 flex items-center justify-center p-1.5 transition-transform duration-200"
      :class="sideways ? 'h-3/4 w-[133.333%]' : 'size-full'"
      :style="{ transform: `translate(-50%, -50%) rotate(${rotation}deg)` }"
    >
      <img
        v-if="src"
        :src="src"
        :alt="`Preview of source page ${source}`"
        class="max-h-full max-w-full rounded-[2px] object-contain shadow-sm ring-1 ring-black/10"
        draggable="false"
      >
      <div v-else class="flex flex-col items-center gap-1 text-ink-muted">
        <UIcon name="i-lucide-file-text" class="size-7" />
        <span class="font-data text-xs tabular-nums">{{ source }}</span>
      </div>
    </div>
  </div>
</template>
