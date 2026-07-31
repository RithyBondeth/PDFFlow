<script setup lang="ts">
/**
 * The hero's evidence panel: one document mid-process.
 *
 * Illustrative, not wired to real state — it exists so a first-time visitor can
 * see what "drop a file, pick a tool, take the result" looks like before they
 * have uploaded anything. Labelled as an example so it is never mistaken for a
 * live job.
 */
const steps = [
  { label: 'Received', state: 'done' },
  { label: 'Compressing', state: 'active' },
  { label: 'Ready', state: 'waiting' },
] as const
</script>

<template>
  <div class="panel overflow-hidden">
    <div class="flex items-center gap-3 border-b border-hairline px-4 py-2.5">
      <span class="font-data text-[11px] text-ink-muted">quarterly-report.pdf</span>
      <span
        class="font-data ml-auto rounded-sm border border-hairline px-1.5 py-0.5 text-[10px] uppercase tracking-[0.14em] text-ink-faint"
      >
        Example
      </span>
    </div>

    <!-- A page rendered as its own text: rules of varying length, with one
         accent band standing in for the region being rewritten. -->
    <div class="px-5 pt-5">
      <div class="trough space-y-2 p-4" aria-hidden="true">
        <div class="h-2 w-2/5 rounded-full bg-ink/25" />
        <div class="h-1.5 w-full rounded-full bg-ink/10" />
        <div class="h-1.5 w-11/12 rounded-full bg-ink/10" />
        <div class="h-1.5 w-4/5 rounded-full bg-accent-500" />
        <div class="h-1.5 w-full rounded-full bg-ink/10" />
        <div class="h-1.5 w-3/5 rounded-full bg-ink/10" />
      </div>
    </div>

    <!-- A genuine three-step sequence, so it is drawn as one: connected, with
         the current step marked. -->
    <ol class="flex items-center gap-2 px-5 pt-4">
      <li
        v-for="(step, index) in steps"
        :key="step.label"
        class="flex flex-1 items-center gap-2"
      >
        <span
          class="size-1.5 shrink-0 rounded-full"
          :class="{
            'bg-good': step.state === 'done',
            'bg-accent-500': step.state === 'active',
            'bg-hairline-strong': step.state === 'waiting',
          }"
          aria-hidden="true"
        />
        <span
          class="font-data whitespace-nowrap text-[10px] uppercase tracking-[0.14em]"
          :class="step.state === 'waiting' ? 'text-ink-faint' : 'text-ink-muted'"
        >
          {{ step.label }}
        </span>
        <span
          v-if="index < steps.length - 1"
          class="h-px flex-1 bg-hairline"
          aria-hidden="true"
        />
      </li>
    </ol>

    <div class="grid grid-cols-3 gap-4 px-5 pt-5">
      <div>
        <p class="font-data text-lg tabular-nums text-ink-muted">
          12.4<span class="text-xs text-ink-faint"> MB</span>
        </p>
        <p class="mt-0.5 text-[11px] text-ink-faint">Before</p>
      </div>
      <div>
        <p class="font-data text-lg tabular-nums text-ink">
          3.9<span class="text-xs text-ink-faint"> MB</span>
        </p>
        <p class="mt-0.5 text-[11px] text-ink-faint">After</p>
      </div>
      <div>
        <p class="font-data text-lg tabular-nums text-good">−68%</p>
        <p class="mt-0.5 text-[11px] text-ink-faint">Saved</p>
      </div>
    </div>

    <div class="mt-5 border-t border-hairline px-5 py-4">
      <TimeFuse label="Then deleted" value="30 min" :burn="34" />
    </div>
  </div>
</template>
