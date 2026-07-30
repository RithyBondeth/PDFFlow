<script setup lang="ts">
import type { Operation } from '~/types/api'

/**
 * Per-tool option form. Kept explicit rather than generated from the JSON
 * schema: each tool has a handful of options and a hand-written control reads
 * far better than a generic schema renderer.
 */
const props = defineProps<{ operation: Operation }>()
const options = defineModel<Record<string, unknown>>({ required: true })

function set(key: string, value: unknown) {
  options.value = { ...options.value, [key]: value }
}

// Sensible defaults so the run button works without touching anything.
watch(
  () => props.operation.key,
  (key) => {
    if (key === 'compress') options.value = { level: 'medium' }
    else if (key === 'rotate') options.value = { angle: 90, pages: '' }
    else if (key === 'split') options.value = { mode: 'every_page', ranges: '' }
    else options.value = {}
  },
  { immediate: true },
)

const COMPRESSION_LEVELS = [
  { value: 'low', label: 'Low', hint: 'Best quality, smallest saving' },
  { value: 'medium', label: 'Medium', hint: 'Recommended balance' },
  { value: 'high', label: 'High', hint: 'Smallest file, softer images' },
]
</script>

<template>
  <div class="panel space-y-5 p-6">
    <h2 class="text-sm font-medium uppercase tracking-wider text-ink-400">
      Options
    </h2>

    <!-- Compress -->
    <div v-if="operation.key === 'compress'" class="grid gap-2 sm:grid-cols-3">
      <button
        v-for="level in COMPRESSION_LEVELS"
        :key="level.value"
        type="button"
        class="rounded-xl border p-3 text-left transition-colors"
        :class="options.level === level.value
          ? 'border-accent-500 bg-accent-500/10'
          : 'border-ink-800 hover:border-ink-700'"
        @click="set('level', level.value)"
      >
        <span class="block font-medium text-ink-200">{{ level.label }}</span>
        <span class="block text-xs text-ink-400">{{ level.hint }}</span>
      </button>
    </div>

    <!-- Rotate -->
    <template v-else-if="operation.key === 'rotate'">
      <UFormField label="Angle">
        <div class="flex gap-2">
          <UButton
            v-for="angle in [90, 180, 270]"
            :key="angle"
            :color="options.angle === angle ? 'primary' : 'neutral'"
            :variant="options.angle === angle ? 'solid' : 'outline'"
            @click="set('angle', angle)"
          >
            {{ angle }}°
          </UButton>
        </div>
      </UFormField>
      <UFormField label="Pages" hint="Leave blank to rotate every page">
        <UInput
          :model-value="(options.pages as string) ?? ''"
          placeholder="e.g. 1-3,7"
          @update:model-value="set('pages', $event)"
        />
      </UFormField>
    </template>

    <!-- Split -->
    <template v-else-if="operation.key === 'split'">
      <UFormField label="How to split">
        <URadioGroup
          :model-value="options.mode"
          :items="[
            { value: 'every_page', label: 'One PDF per page' },
            { value: 'ranges', label: 'By page range' },
          ]"
          @update:model-value="set('mode', $event)"
        />
      </UFormField>
      <UFormField
        v-if="options.mode === 'ranges'"
        label="Ranges"
        hint="Each range becomes its own PDF"
      >
        <UInput
          :model-value="(options.ranges as string) ?? ''"
          placeholder="e.g. 1-3,4-6,7"
          @update:model-value="set('ranges', $event)"
        />
      </UFormField>
    </template>

    <!-- Extract pages -->
    <UFormField
      v-else-if="operation.key === 'extract_pages'"
      label="Pages to keep"
      hint="Blank keeps every page"
    >
      <UInput
        :model-value="(options.pages as string) ?? ''"
        placeholder="e.g. 2,5-9"
        @update:model-value="set('pages', $event)"
      />
    </UFormField>

    <p v-else class="text-sm text-ink-400">
      This tool has no options — just run it.
    </p>
  </div>
</template>
