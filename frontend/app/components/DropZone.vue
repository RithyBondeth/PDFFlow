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
    class="panel relative overflow-hidden px-5 py-8 text-center transition-colors duration-200 sm:px-7 sm:py-6 sm:text-left"
    :class="[
      isOver
        ? 'border-accent-400 shadow-[0_0_0_1px_oklch(0.822_0.145_79/0.5),0_0_60px_-12px_oklch(0.772_0.155_76/0.55)]'
        : 'hover:border-line-lit',
      disabled && 'pointer-events-none opacity-50',
    ]"
    @dragenter.prevent="((depth++), (isOver = true))"
    @dragover.prevent
    @dragleave.prevent="(--depth <= 0) && (isOver = false)"
    @drop.prevent="onDrop"
  >
    <!-- The tray this drops into. It brightens on drag-over so the whole panel
         confirms the drop target, not just the border. -->
    <div
      class="pointer-events-none absolute inset-0 transition-opacity duration-300"
      :class="isOver ? 'opacity-100' : 'opacity-0'"
      aria-hidden="true"
      style="
        background: radial-gradient(
          40rem 14rem at 50% 0%,
          oklch(0.772 0.155 76 / 0.14),
          transparent 70%
        );
      "
    />

    <!-- Wide bar at sm+, stacked on mobile. The whole panel is the drop target
         either way; the button is only there for people who would rather pick. -->
    <div class="relative flex flex-col items-center gap-5 sm:flex-row sm:gap-6">
      <div
        class="flex size-12 shrink-0 items-center justify-center rounded-full border border-accent-500/35 bg-accent-500/10 text-accent-300 transition-transform duration-300 ease-out"
        :class="isOver && 'scale-110'"
      >
        <UIcon name="i-lucide-upload" class="size-5" />
      </div>

      <div class="min-w-0 space-y-1 sm:flex-1">
        <p class="font-display text-xl font-bold tracking-tight text-paper">
          {{ isOver ? 'Let go to upload' : 'Drop a file to start' }}
        </p>
        <p class="text-sm text-paper-dim">
          PDF, images or Office documents — up to
          {{ formatBytes(maxBytes) }} each
        </p>
      </div>

      <div class="flex shrink-0 flex-col items-center gap-2">
        <UButton
          color="primary"
          size="lg"
          icon="i-lucide-folder-open"
          class="shadow-[0_0_30px_-8px_oklch(0.772_0.155_76/0.65)] hover:-translate-y-0.5 hover:shadow-[0_0_38px_-6px_oklch(0.772_0.155_76/0.8)]"
          @click="input?.click()"
        >
          Choose files
        </UButton>
        <p class="font-data text-[10px] uppercase tracking-[0.14em] text-paper-faint">
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
