<script setup lang="ts">
/**
 * The hero's thesis object: one document under the safelight, mid-process.
 *
 * Illustrative, not wired to real state — it exists so a first-time visitor can
 * see what "drop a file, pick a tool, take the result" looks like before they
 * have uploaded anything. Everything in it is labelled as an example so it is
 * never mistaken for a live job.
 */
const steps = [
  { label: 'Received', state: 'done' },
  { label: 'Compressing', state: 'active' },
  { label: 'Ready', state: 'waiting' },
] as const
</script>

<template>
  <div class="panel overflow-hidden">
    <div class="flex items-center gap-3 border-b border-line px-4 py-2.5">
      <span class="flex gap-1.5" aria-hidden="true">
        <span class="size-2 rounded-full bg-line-lit" />
        <span class="size-2 rounded-full bg-line-lit" />
        <span class="size-2 rounded-full bg-accent-500/70" />
      </span>
      <span class="font-data text-[11px] text-paper-faint">quarterly-report.pdf</span>
      <span
        class="font-data ml-auto rounded border border-line px-1.5 py-0.5 text-[10px] uppercase tracking-[0.14em] text-paper-faint"
      >
        Example
      </span>
    </div>

    <!-- The sheet, developing. The sweep is the only ambient motion on the
         page: one slow pass of the safelight across the page being worked on. -->
    <div class="relative overflow-hidden px-5 pt-5">
      <div class="trough relative overflow-hidden p-4">
        <div
          class="sweep pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 skew-x-[-14deg]"
          aria-hidden="true"
          style="
            background: linear-gradient(
              90deg,
              transparent,
              oklch(0.822 0.145 79 / 0.16),
              transparent
            );
          "
        />

        <!-- A page rendered as its own text: rules of varying length, one
             highlighted band standing in for the region being rewritten. -->
        <div class="relative space-y-2" aria-hidden="true">
          <div class="h-2 w-2/5 rounded-full bg-paper/25" />
          <div class="h-1.5 w-full rounded-full bg-paper/10" />
          <div class="h-1.5 w-11/12 rounded-full bg-paper/10" />
          <div class="h-1.5 w-4/5 rounded-full bg-accent-400/45" />
          <div class="h-1.5 w-full rounded-full bg-paper/10" />
          <div class="h-1.5 w-3/5 rounded-full bg-paper/10" />
        </div>
      </div>
    </div>

    <!-- Where the job is. A genuine three-step sequence, so it is drawn as
         one: connected, with the current step lit. -->
    <ol class="flex items-center gap-2 px-5 pt-4">
      <li
        v-for="(step, index) in steps"
        :key="step.label"
        class="flex flex-1 items-center gap-2"
      >
        <span
          class="size-1.5 shrink-0 rounded-full"
          :class="{
            'bg-fixer': step.state === 'done',
            'bg-accent-400 shadow-[0_0_8px_1px_oklch(0.822_0.145_79/0.7)]': step.state === 'active',
            'bg-line-lit': step.state === 'waiting',
          }"
          aria-hidden="true"
        />
        <span
          class="font-data whitespace-nowrap text-[10px] uppercase tracking-[0.14em]"
          :class="step.state === 'waiting' ? 'text-paper-faint' : 'text-paper-dim'"
        >
          {{ step.label }}
        </span>
        <span
          v-if="index < steps.length - 1"
          class="h-px flex-1 bg-line"
          aria-hidden="true"
        />
      </li>
    </ol>

    <div class="grid grid-cols-3 gap-4 px-5 pt-5">
      <div>
        <p class="font-data text-lg tabular-nums text-paper-dim">
          12.4<span class="text-xs text-paper-faint"> MB</span>
        </p>
        <p class="mt-0.5 text-[11px] text-paper-faint">Before</p>
      </div>
      <div>
        <p class="font-data text-lg tabular-nums text-paper">
          3.9<span class="text-xs text-paper-faint"> MB</span>
        </p>
        <p class="mt-0.5 text-[11px] text-paper-faint">After</p>
      </div>
      <div>
        <p class="font-data text-lg tabular-nums text-fixer">−68%</p>
        <p class="mt-0.5 text-[11px] text-paper-faint">Saved</p>
      </div>
    </div>

    <div class="mt-5 border-t border-line px-5 py-4">
      <TimeFuse label="Then deleted" value="30 min" :burn="34" />
    </div>
  </div>
</template>
