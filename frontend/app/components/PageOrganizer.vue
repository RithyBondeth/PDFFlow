<script setup lang="ts">
import type { OrganizedPage } from '~/utils/pageOrganizer'
import {
  duplicatePage,
  movePage,
  removePage,
  rotatePage,
} from '~/utils/pageOrganizer'

const pages = defineModel<OrganizedPage[]>({ required: true })
const dragIndex = ref<number | null>(null)

function onDrop(target: number) {
  if (dragIndex.value !== null) pages.value = movePage(pages.value, dragIndex.value, target)
  dragIndex.value = null
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div>
        <p class="text-sm font-medium text-ink">Output page order</p>
        <p class="text-xs text-ink-muted">
          Drag cards to reorder. Rotate, copy or remove any page.
        </p>
      </div>
      <span class="font-data rounded-full border border-hairline px-2.5 py-1 text-[10px] uppercase tracking-[0.1em] text-ink-faint">
        {{ pages.length }} {{ pages.length === 1 ? 'page' : 'pages' }}
      </span>
    </div>

    <ol class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
      <li
        v-for="(page, index) in pages"
        :key="`${page.source}-${index}`"
        class="group rounded-md border border-hairline bg-raised p-2 transition-colors hover:border-hairline-strong"
        :class="dragIndex === index ? 'opacity-40' : ''"
        draggable="true"
        @dragstart="dragIndex = index"
        @dragover.prevent
        @drop.prevent="onDrop(index)"
        @dragend="dragIndex = null"
      >
        <div class="mb-2 flex items-center justify-between gap-2">
          <span class="font-data text-[10px] tabular-nums uppercase tracking-[0.1em] text-accent-ink">
            Output {{ index + 1 }}
          </span>
          <UIcon name="i-lucide-grip-horizontal" class="size-3.5 cursor-grab text-ink-faint" />
        </div>

        <div class="flex aspect-[3/4] items-center justify-center rounded border border-hairline bg-surface">
          <div
            class="flex flex-col items-center gap-1 text-ink-muted transition-transform"
            :style="{ transform: `rotate(${page.rotation}deg)` }"
          >
            <UIcon name="i-lucide-file-text" class="size-7" />
            <span class="font-data text-xs tabular-nums">{{ page.source }}</span>
          </div>
        </div>

        <p class="mt-2 truncate text-center text-xs text-ink-muted">
          Source page {{ page.source }}<template v-if="page.rotation"> · {{ page.rotation }}°</template>
        </p>

        <div class="mt-2 grid grid-cols-5 gap-1">
          <UButton
            color="neutral"
            variant="ghost"
            size="xs"
            icon="i-lucide-arrow-left"
            :disabled="index === 0"
            :aria-label="`Move source page ${page.source} left`"
            @click="pages = movePage(pages, index, index - 1)"
          />
          <UButton
            color="neutral"
            variant="ghost"
            size="xs"
            icon="i-lucide-arrow-right"
            :disabled="index === pages.length - 1"
            :aria-label="`Move source page ${page.source} right`"
            @click="pages = movePage(pages, index, index + 1)"
          />
          <UButton
            color="neutral"
            variant="ghost"
            size="xs"
            icon="i-lucide-rotate-cw"
            :aria-label="`Rotate source page ${page.source}`"
            @click="pages = rotatePage(pages, index)"
          />
          <UButton
            color="neutral"
            variant="ghost"
            size="xs"
            icon="i-lucide-copy-plus"
            :aria-label="`Duplicate source page ${page.source}`"
            @click="pages = duplicatePage(pages, index)"
          />
          <UButton
            color="neutral"
            variant="ghost"
            size="xs"
            icon="i-lucide-trash-2"
            :disabled="pages.length === 1"
            :aria-label="`Remove source page ${page.source}`"
            @click="pages = removePage(pages, index)"
          />
        </div>
      </li>
    </ol>
  </div>
</template>
