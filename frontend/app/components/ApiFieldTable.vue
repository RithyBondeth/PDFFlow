<script setup lang="ts">
import type { DocField } from '~/utils/apiReference'

defineProps<{ label: string; fields: DocField[] }>()
</script>

<template>
  <section>
    <div class="mb-3 flex items-baseline gap-3">
      <h4 class="font-data text-[11px] uppercase tracking-[0.18em] text-paper-faint">
        {{ label }}
      </h4>
      <span class="h-px flex-1 bg-line" aria-hidden="true" />
    </div>

    <!-- A definition list rather than a table: two of these columns are one
         short phrase each, and a real table drops to unreadable widths on a
         phone. -->
    <dl class="space-y-2.5">
      <div
        v-for="field in fields"
        :key="field.name"
        class="grid gap-x-4 gap-y-1 sm:grid-cols-[minmax(0,15rem)_1fr]"
      >
        <dt class="flex flex-wrap items-baseline gap-x-2">
          <code class="font-data text-[13px] text-paper">{{ field.name }}</code>
          <span class="font-data text-[11px] text-accent-300/80">{{ field.type }}</span>
          <span v-if="field.note" class="font-data text-[11px] text-paper-faint">
            {{ field.note }}
          </span>
        </dt>
        <dd class="text-sm leading-relaxed text-paper-dim">
          <DocProse :text="field.description" />
        </dd>
      </div>
    </dl>
  </section>
</template>
