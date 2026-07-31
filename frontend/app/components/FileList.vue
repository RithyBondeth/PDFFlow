<script setup lang="ts">
import type { UploadedFile } from '~/types/api'

defineProps<{ files: UploadedFile[]; reorderable?: boolean }>()
const emit = defineEmits<{ remove: [string]; reorder: [number, number] }>()

const dragIndex = ref<number | null>(null)

function onDrop(target: number) {
  if (dragIndex.value !== null && dragIndex.value !== target) {
    emit('reorder', dragIndex.value, target)
  }
  dragIndex.value = null
}
</script>

<template>
  <ul class="space-y-2">
    <li
      v-for="(file, index) in files"
      :key="file.id"
      class="panel lift group flex items-center gap-3 px-3.5 py-3"
      :class="
        dragIndex === index
          ? 'border-accent-500 opacity-40'
          : 'hover:border-hairline-strong'
      "
      :draggable="reorderable"
      @dragstart="dragIndex = index"
      @dragover.prevent
      @drop.prevent="onDrop(index)"
      @dragend="dragIndex = null"
    >
      <UIcon
        v-if="reorderable"
        name="i-lucide-grip-vertical"
        class="size-4 shrink-0 cursor-grab text-ink-faint transition-colors group-hover:text-ink-muted"
        aria-hidden="true"
      />
      <!-- Position only appears when order is load-bearing, i.e. when the
           selected tool combines files. -->
      <span
        v-if="reorderable"
        class="font-data w-4 shrink-0 text-center text-[11px] tabular-nums text-accent-ink"
      >{{ index + 1 }}</span>

      <UIcon
        :name="FAMILY_ICONS[file.family] ?? 'i-lucide-file'"
        class="size-4 shrink-0 text-ink-muted"
      />

      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-ink" :title="file.originalName">
          {{ file.originalName }}
        </p>
        <p class="font-data text-[11px] tabular-nums text-ink-faint">
          {{ formatBytes(file.size) }}
          <template v-if="file.pageCount"> · {{ file.pageCount }} pages</template>
        </p>
      </div>

      <UButton
        color="neutral"
        variant="ghost"
        icon="i-lucide-x"
        size="xs"
        :aria-label="`Remove ${file.originalName}`"
        @click="emit('remove', file.id)"
      />
    </li>
  </ul>
</template>
