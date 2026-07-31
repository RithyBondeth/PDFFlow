<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    accept?: string
    multiple?: boolean
    maxBytes?: number
    disabled?: boolean
  }>(),
  {
    accept: '.pdf,.jpg,.jpeg,.png,.webp,.docx,.xlsx,.pptx',
    multiple: true,
    maxBytes: 100 * 1024 * 1024,
    disabled: false,
  },
)

const emit = defineEmits<{ files: [File[]]; error: [string] }>()

const input = ref<HTMLInputElement>()
const isOver = ref(false)
// Nested dragenter/dragleave pairs fire constantly; counting them is the only
// reliable way to know when the pointer has truly left the zone.
let depth = 0

function accepted(list: FileList | null): File[] {
  const files = Array.from(list ?? [])
  if (!files.length) return []

  const tooLarge = files.find((file) => file.size > props.maxBytes)
  if (tooLarge) {
    emit('error', `“${tooLarge.name}” is larger than ${formatBytes(props.maxBytes)}.`)
    return []
  }
  return props.multiple ? files : files.slice(0, 1)
}

function onDrop(event: DragEvent) {
  depth = 0
  isOver.value = false
  if (props.disabled) return
  const files = accepted(event.dataTransfer?.files ?? null)
  if (files.length) emit('files', files)
}

function onSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const files = accepted(target.files)
  if (files.length) emit('files', files)
  target.value = '' // allow re-picking the same file
}
</script>

<template>
  <div
    class="panel px-5 py-8 text-center transition-colors duration-200 sm:px-7 sm:py-6 sm:text-left"
    :class="[
      isOver ? 'border-accent-500 bg-accent-500/[0.05]' : 'hover:border-hairline-strong',
      disabled && 'pointer-events-none opacity-50',
    ]"
    @dragenter.prevent="((depth++), (isOver = true))"
    @dragover.prevent
    @dragleave.prevent="(--depth <= 0) && (isOver = false)"
    @drop.prevent="onDrop"
  >
    <!-- Wide bar at sm+, stacked on mobile. The whole panel is the drop target
         either way; the button is only there for people who would rather pick. -->
    <div class="flex flex-col items-center gap-5 sm:flex-row sm:gap-6">
      <div
        class="flex size-11 shrink-0 items-center justify-center rounded-md transition-colors duration-200"
        :class="isOver ? 'bg-accent-500 text-white' : 'bg-raised text-ink-muted'"
      >
        <UIcon name="i-lucide-upload" class="size-5" />
      </div>

      <div class="min-w-0 space-y-1 sm:flex-1">
        <p class="font-display text-lg font-medium tracking-[-0.02em] text-ink">
          {{ isOver ? 'Let go to upload' : 'Drop a file to start' }}
        </p>
        <p class="text-sm text-ink-muted">
          PDF, images or Office documents — up to
          {{ formatBytes(maxBytes) }} each
        </p>
      </div>

      <div class="flex shrink-0 flex-col items-center gap-2">
        <UButton
          color="primary"
          size="lg"
          icon="i-lucide-folder-open"
          @click="input?.click()"
        >
          Choose files
        </UButton>
        <p class="font-data text-[10px] uppercase tracking-[0.14em] text-ink-faint">
          No account needed
        </p>
      </div>
    </div>

    <input
      ref="input"
      type="file"
      class="sr-only"
      :accept="accept"
      :multiple="multiple"
      @change="onSelect"
    >
  </div>
</template>
