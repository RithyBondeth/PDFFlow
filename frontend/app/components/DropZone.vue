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
    class="panel relative flex flex-col items-center justify-center gap-4 px-8 py-14 text-center transition-colors"
    :class="[
      isOver ? 'border-accent-500 bg-accent-500/5' : 'hover:border-ink-700',
      disabled && 'pointer-events-none opacity-50',
    ]"
    @dragenter.prevent="((depth++), (isOver = true))"
    @dragover.prevent
    @dragleave.prevent="(--depth <= 0) && (isOver = false)"
    @drop.prevent="onDrop"
  >
    <div
      class="flex size-14 items-center justify-center rounded-full bg-accent-500/10 text-accent-600 transition-transform"
      :class="isOver && 'scale-110'"
    >
      <UIcon name="i-lucide-upload-cloud" class="size-7" />
    </div>

    <div class="space-y-1">
      <p class="text-lg font-medium text-ink-200">
        Drop your files here
      </p>
      <p class="text-sm text-ink-400">
        PDF, images, or Office documents — up to {{ formatBytes(maxBytes) }} each
      </p>
    </div>

    <UButton
      color="primary"
      size="lg"
      icon="i-lucide-folder-open"
      @click="input?.click()"
    >
      Choose files
    </UButton>

    <p class="text-xs text-ink-400">
      Processed on our server, then deleted automatically. No account needed.
    </p>

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
