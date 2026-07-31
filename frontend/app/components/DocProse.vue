<script setup lang="ts">
/**
 * Renders a reference description, turning `backticked` spans into inline code.
 *
 * The alternative was authoring HTML in apiReference.ts and dropping it in with
 * v-html; splitting on backticks keeps the data plain text and the escaping
 * Vue's problem rather than mine.
 */
const props = defineProps<{ text: string }>()

const parts = computed(() =>
  props.text
    .split(/`([^`]+)`/g)
    // The capture group lands on every odd index, so position is the marker.
    .map((value, index) => ({ value, code: index % 2 === 1 }))
    .filter((part) => part.value !== ''),
)
</script>

<template>
  <span>
    <template v-for="(part, index) in parts" :key="index">
      <code v-if="part.code" class="font-data text-[0.9em] text-paper">{{ part.value }}</code>
      <template v-else>{{ part.value }}</template>
    </template>
  </span>
</template>
