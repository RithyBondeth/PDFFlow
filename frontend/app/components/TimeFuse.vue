<script setup lang="ts">
/**
 * The fuse: a lit rail showing how much of a file's short life is spent.
 *
 * Two uses, deliberately the same object. On the landing page it is static and
 * simply states the 30-minute limit. In the workspace `burn` is driven by the
 * real expiry, so the rail a visitor saw on the way in turns out to have been
 * telling the truth.
 */
const props = withDefaults(
  defineProps<{
    /** How much of the lifetime is gone, 0–100. */
    burn?: number
    label: string
    /** Right-hand readout — a countdown, or a fixed limit on the landing page. */
    value?: string
  }>(),
  { burn: 0 },
)

const clamped = computed(() => Math.min(100, Math.max(0, props.burn)))
</script>

<template>
  <div class="space-y-2">
    <div class="flex items-baseline justify-between gap-4">
      <span class="font-data text-[11px] uppercase tracking-[0.18em] text-ink-faint">
        {{ label }}
      </span>
      <span v-if="value" class="font-data text-xs tabular-nums text-accent-ink">
        {{ value }}
      </span>
    </div>
    <div class="fuse" :style="{ '--burn': `${clamped}%` }" aria-hidden="true" />
  </div>
</template>
