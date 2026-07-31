<script setup lang="ts">
const links = [
  { label: 'Tools', to: '/#tools' },
  { label: 'How it works', to: '/#lifecycle' },
  { label: 'API', to: '/api-docs' },
] as const
</script>

<template>
  <header class="sticky top-0 z-50 border-b border-line/80 bg-canvas/70 backdrop-blur-xl">
    <div class="mx-auto flex h-16 max-w-6xl items-center gap-6 px-5 sm:px-6">
      <NuxtLink to="/" class="group flex items-center gap-2.5" aria-label="PDFFlow home">
        <!-- The mark is a sheet under the safelight: a lit top edge, a body that
             fades into the room. -->
        <span
          class="relative flex size-8 items-center justify-center rounded-[7px] border border-accent-500/40 bg-gradient-to-b from-accent-400/25 to-transparent text-accent-300 transition-colors duration-200 group-hover:border-accent-400/70"
        >
          <UIcon name="i-lucide-layers" class="size-4" />
        </span>
        <span class="font-display text-lg tracking-tight">
          <span class="font-extrabold text-paper">PDF</span><span class="font-medium text-paper-faint">Flow</span>
        </span>
      </NuxtLink>

      <nav class="ml-auto hidden items-center gap-1 text-sm sm:flex">
        <UButton
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          variant="ghost"
          color="neutral"
          class="text-paper-dim hover:text-paper"
        >
          {{ link.label }}
        </UButton>
      </nav>

      <UButton
        to="/#upload"
        color="primary"
        class="ml-auto shadow-[0_0_24px_-6px_oklch(0.772_0.155_76/0.55)] hover:shadow-[0_0_30px_-4px_oklch(0.772_0.155_76/0.7)] sm:ml-0"
      >
        Add a file
      </UButton>
    </div>
  </header>
</template>
