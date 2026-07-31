<script setup lang="ts">
/**
 * Light/dark switch.
 *
 * `colorMode.preference` is what the visitor chose ('system' until they choose);
 * `colorMode.value` is what that resolves to right now. Writing the resolved
 * value on click means the first press always flips what is on screen rather
 * than doing nothing because the stored preference was already 'dark'.
 */
const colorMode = useColorMode()

const isDark = computed(() => colorMode.value === 'dark')

function toggle() {
  colorMode.preference = isDark.value ? 'light' : 'dark'
}
</script>

<template>
  <!-- The server cannot know the visitor's mode, so rendering the icon there
       would guarantee a hydration mismatch and a flash of the wrong glyph.
       ClientOnly with a same-size placeholder keeps the header from shifting. -->
  <ClientOnly>
    <button
      type="button"
      class="flex size-8 items-center justify-center rounded-[5px] border border-hairline text-ink-muted transition-colors duration-200 hover:border-hairline-strong hover:text-ink"
      :aria-label="isDark ? 'Switch to light theme' : 'Switch to dark theme'"
      :aria-pressed="isDark"
      @click="toggle"
    >
      <UIcon :name="isDark ? 'i-lucide-sun' : 'i-lucide-moon'" class="size-4" />
    </button>

    <template #fallback>
      <div class="size-8 rounded-[5px] border border-hairline" aria-hidden="true" />
    </template>
  </ClientOnly>
</template>
