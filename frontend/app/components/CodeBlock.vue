<script setup lang="ts">
import type { DocSample } from '~/utils/apiReference'

/**
 * A code panel with tabs when a snippet has more than one form (curl, the
 * response, the browser equivalent) and a copy button that always copies the
 * tab you are looking at.
 */
const props = defineProps<{ samples: DocSample[] }>()

const active = ref(0)
const copied = ref(false)
let resetTimer: ReturnType<typeof setTimeout> | undefined

const current = computed(() => props.samples[active.value] ?? props.samples[0]!)
const rendered = computed(() => highlight(current.value.code, current.value.language))

async function copy() {
  try {
    await navigator.clipboard.writeText(current.value.code)
    copied.value = true
    clearTimeout(resetTimer)
    resetTimer = setTimeout(() => (copied.value = false), 1600)
  } catch {
    // A denied clipboard permission is not worth an error state — the text is
    // selectable, which is the fallback either way.
    copied.value = false
  }
}

onScopeDispose(() => clearTimeout(resetTimer))
</script>

<template>
  <div class="trough overflow-hidden">
    <div class="flex items-center gap-1 border-b border-hairline px-2 py-1.5">
      <button
        v-for="(sample, index) in samples"
        :key="sample.label"
        type="button"
        class="font-data rounded px-2 py-1 text-[11px] uppercase tracking-[0.14em] transition-colors duration-150"
        :class="
          index === active
            ? 'bg-accent-500/12 text-accent-ink'
            : 'text-ink-faint hover:text-ink-muted'
        "
        :aria-pressed="index === active"
        @click="active = index"
      >
        {{ sample.label }}
      </button>

      <button
        type="button"
        class="font-data ml-auto flex items-center gap-1.5 rounded px-2 py-1 text-[11px] uppercase tracking-[0.14em] transition-colors duration-150"
        :class="copied ? 'text-good' : 'text-ink-faint hover:text-ink-muted'"
        @click="copy"
      >
        <UIcon :name="copied ? 'i-lucide-check' : 'i-lucide-copy'" class="size-3.5" />
        {{ copied ? 'Copied' : 'Copy' }}
      </button>
    </div>

    <!-- Authored content, escaped by highlight() before any markup is added. -->
    <pre
      class="overflow-x-auto px-4 py-3.5 text-[13px] leading-relaxed"
    ><code class="font-data" v-html="rendered" /></pre>
  </div>
</template>

<style scoped>
/* Scoped to the snippets so the token colours cannot leak into page text.
   The accent goes to strings — the part of a snippet a reader is most likely to
   be substituting their own value into. Each token needs a light and a dark
   shade: what reads well on #f7f8f9 is washed out on #151618. */
:deep(.tok-string) {
  color: var(--color-accent-700);
}

:deep(.tok-key) {
  color: var(--color-ink);
}

:deep(.tok-keyword),
:deep(.tok-number) {
  color: oklch(0.45 0.13 300);
}

:deep(.tok-flag) {
  color: var(--color-ink-muted);
}

:deep(.tok-comment) {
  color: var(--color-ink-faint);
  font-style: italic;
}

:global(.dark) :deep(.tok-string) {
  color: var(--color-accent-200);
}

:global(.dark) :deep(.tok-keyword),
:global(.dark) :deep(.tok-number) {
  color: oklch(0.82 0.11 300);
}
</style>
