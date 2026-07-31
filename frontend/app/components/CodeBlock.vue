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
    <div class="flex items-center gap-1 border-b border-line px-2 py-1.5">
      <button
        v-for="(sample, index) in samples"
        :key="sample.label"
        type="button"
        class="font-data rounded px-2 py-1 text-[11px] uppercase tracking-[0.14em] transition-colors duration-150"
        :class="
          index === active
            ? 'bg-accent-500/12 text-accent-300'
            : 'text-paper-faint hover:text-paper-dim'
        "
        :aria-pressed="index === active"
        @click="active = index"
      >
        {{ sample.label }}
      </button>

      <button
        type="button"
        class="font-data ml-auto flex items-center gap-1.5 rounded px-2 py-1 text-[11px] uppercase tracking-[0.14em] transition-colors duration-150"
        :class="copied ? 'text-fixer' : 'text-paper-faint hover:text-paper-dim'"
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
   The safelight is reserved for strings — the part of a snippet a reader is
   most likely to be substituting their own value into. */
:deep(.tok-string) {
  color: var(--color-accent-200);
}

:deep(.tok-key) {
  color: var(--color-paper);
}

:deep(.tok-keyword) {
  color: var(--color-fixer);
}

:deep(.tok-number) {
  color: var(--color-fixer);
}

:deep(.tok-flag) {
  color: var(--color-paper-dim);
}

:deep(.tok-comment) {
  color: var(--color-paper-faint);
  font-style: italic;
}
</style>
