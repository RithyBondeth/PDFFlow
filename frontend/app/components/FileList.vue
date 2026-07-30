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
      class="panel flex items-center gap-3 px-4 py-3 transition-opacity"
      :class="dragIndex === index && 'opacity-40'"
      :draggable="reorderable"
      @dragstart="dragIndex = index"
      @dragover.prevent
      @drop.prevent="onDrop(index)"
      @dragend="dragIndex = null"
    >
      <UIcon
        v-if="reorderable"
        name="i-lucide-grip-vertical"
        class="size-4 shrink-0 cursor-grab text-ink-700"
        aria-hidden="true"
      />
      <span
        v-if="reorderable"
        class="w-5 shrink-0 text-center text-xs tabular-nums text-ink-400"
      >{{ index + 1 }}</span>

      <UIcon
        :name="FAMILY_ICONS[file.family] ?? 'i-lucide-file'"
        class="size-5 shrink-0 text-accent-400"
      />

      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-ink-200" :title="file.originalName">
          {{ file.originalName }}
        </p>
        <p class="text-xs text-ink-400">
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
