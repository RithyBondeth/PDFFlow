<script setup lang="ts">
import type {
  WatermarkAngle,
  WatermarkColor,
  WatermarkLayout,
  WatermarkSize,
} from '~/utils/watermarkLayout'
import {
  FONT_ASCENDER,
  WATERMARK_COLORS,
  imageMark,
  positions,
  rotatedBox,
  targetWidth,
  textMark,
} from '~/utils/watermarkLayout'

/**
 * Page 1 with the watermark drawn where the server will draw it, using the
 * same layout rules. Rendered entirely in the browser from the user's files.
 */
const props = defineProps<{
  pdf: File | null
  image: File | null
  mode: 'text' | 'image'
  text: string
  color: WatermarkColor
  size: WatermarkSize
  opacity: number
  angle: WatermarkAngle
  layout: WatermarkLayout
}>()

const { thumbnails, sizes, unavailable, request } = usePdfThumbnails(() => props.pdf)
watch(() => props.pdf, () => request(1), { immediate: true })

// Until page 1 has been measured, assume A4 so the frame does not jump much.
const page = computed(() => sizes.get(1) ?? { width: 595, height: 842 })

// The image's own object URL, released whenever it changes or we unmount.
const imageUrl = ref<string | null>(null)
const imageAspect = ref(1)
watch(
  () => props.image,
  (file, _, onCleanup) => {
    imageUrl.value = null
    if (!file || !import.meta.client) return
    const url = URL.createObjectURL(file)
    const probe = new Image()
    probe.onload = () => {
      imageAspect.value = probe.naturalHeight / Math.max(1, probe.naturalWidth)
      imageUrl.value = url
    }
    probe.src = url
    onCleanup(() => URL.revokeObjectURL(url))
  },
  { immediate: true },
)

// The server draws Helvetica Bold; Arial shares its metrics, so measuring
// either gives the advance width the server will use.
let measurer: CanvasRenderingContext2D | null = null
function widthAtOnePoint(text: string): number {
  if (!import.meta.client) return 0
  measurer ??= document.createElement('canvas').getContext('2d')
  if (!measurer) return 0
  measurer.font = 'bold 100px Helvetica, Arial, sans-serif'
  return measurer.measureText(text).width / 100
}

const displayText = computed(() => props.text.split(/\s+/).filter(Boolean).join(' '))

const mark = computed(() => {
  const target = targetWidth(page.value, props.angle, props.layout, props.size)
  if (props.mode === 'image') return imageMark(imageAspect.value, target, page.value.height)
  if (!displayText.value) return null
  return textMark(widthAtOnePoint(displayText.value), target, page.value.height)
})

const placements = computed(() => {
  if (!mark.value) return []
  const box = rotatedBox(mark.value.width, mark.value.height, props.angle)
  return positions(page.value, box, props.layout)
})
</script>

<template>
  <figure class="space-y-2">
    <div
      class="relative mx-auto w-full max-w-[260px] overflow-hidden rounded border border-hairline bg-white shadow-sm"
      :style="{ aspectRatio: `${page.width} / ${page.height}` }"
    >
      <img
        v-if="thumbnails.get(1)"
        :src="thumbnails.get(1)"
        alt=""
        class="absolute inset-0 size-full object-fill"
        draggable="false"
      >
      <svg
        class="absolute inset-0 size-full"
        :viewBox="`0 0 ${page.width} ${page.height}`"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <g
          v-for="(point, index) in placements"
          :key="index"
          :transform="`translate(${point.x} ${point.y}) rotate(${-angle})`"
        >
          <image
            v-if="mode === 'image' && imageUrl && mark"
            :href="imageUrl"
            :x="-mark.width / 2"
            :y="-mark.height / 2"
            :width="mark.width"
            :height="mark.height"
            :opacity="opacity"
            preserveAspectRatio="none"
          />
          <text
            v-else-if="mode === 'text' && mark?.fontSize"
            :x="-mark.width / 2"
            :y="-mark.height / 2 + mark.fontSize * FONT_ASCENDER"
            :font-size="mark.fontSize"
            :textLength="mark.width"
            lengthAdjust="spacingAndGlyphs"
            font-family="Helvetica, Arial, sans-serif"
            font-weight="700"
            :fill="WATERMARK_COLORS[color]"
            :fill-opacity="opacity"
          >{{ displayText }}</text>
        </g>
      </svg>
    </div>
    <figcaption class="text-center text-xs text-ink-faint">
      {{ unavailable ? 'Preview unavailable for this PDF' : 'Preview of page 1' }}
    </figcaption>
  </figure>
</template>
