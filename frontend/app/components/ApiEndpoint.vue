<script setup lang="ts">
import type { DocEndpoint } from '~/utils/apiReference'

const props = defineProps<{ endpoint: DocEndpoint }>()

// GET reads, POST changes something. The safelight marks the action, exactly as
// it does on a button, so a scan down the page shows what has consequences.
const isWrite = computed(() => props.endpoint.method === 'POST')

/** Splits the path so the parameter segments can be lit differently. */
const segments = computed(() =>
  props.endpoint.path.split(/(\{[^}]+\})/).filter(Boolean).map((part) => ({
    text: part,
    param: part.startsWith('{'),
  })),
)
</script>

<template>
  <article :id="endpoint.id" class="panel scroll-mt-24 p-5 sm:p-6">
    <header class="flex flex-wrap items-center gap-3">
      <span
        class="font-data rounded px-2 py-1 text-[11px] font-medium uppercase tracking-[0.14em]"
        :class="
          isWrite
            ? 'border border-accent-500/40 bg-accent-500/12 text-accent-ink'
            : 'border border-hairline bg-canvas/60 text-ink-muted'
        "
      >
        {{ endpoint.method }}
      </span>

      <code class="font-data text-sm text-ink">
        <span
          v-for="(segment, index) in segments"
          :key="index"
          :class="segment.param ? 'text-accent-ink' : ''"
        >{{ segment.text }}</span>
      </code>

      <span
        v-if="endpoint.rateLimit"
        class="font-data ml-auto text-[11px] uppercase tracking-[0.14em] text-ink-faint"
      >
        {{ endpoint.rateLimit }}
      </span>
    </header>

    <h3 class="font-display mt-4 text-xl font-bold tracking-tight text-ink">
      {{ endpoint.summary }}
    </h3>
    <p class="mt-2 max-w-2xl text-pretty leading-relaxed text-ink-muted">
      <DocProse :text="endpoint.description" />
    </p>

    <div class="mt-5 space-y-5">
      <ApiFieldTable
        v-if="endpoint.pathParams?.length"
        label="Path parameters"
        :fields="endpoint.pathParams"
      />

      <ApiFieldTable
        v-if="endpoint.body"
        :label="`Body — ${endpoint.body.contentType}`"
        :fields="endpoint.body.fields"
      />

      <CodeBlock :samples="endpoint.samples" />

      <ApiFieldTable
        v-if="endpoint.returns?.length"
        :label="`Returns ${endpoint.responds.status} — ${endpoint.responds.description}`"
        :fields="endpoint.returns"
      />
      <div v-else class="flex items-baseline gap-3">
        <span class="font-data text-[11px] uppercase tracking-[0.18em] text-ink-faint">
          Returns
        </span>
        <span class="font-data text-xs text-ink-muted">
          {{ endpoint.responds.status }} — {{ endpoint.responds.description }}
        </span>
      </div>

      <div v-if="endpoint.errors?.length" class="flex flex-wrap items-baseline gap-x-3 gap-y-2">
        <span class="font-data text-[11px] uppercase tracking-[0.18em] text-ink-faint">
          Can fail with
        </span>
        <span
          v-for="error in endpoint.errors"
          :key="error"
          class="font-data rounded border border-hairline px-2 py-0.5 text-[11px] text-ink-muted"
        >
          {{ error }}
        </span>
      </div>
    </div>
  </article>
</template>
