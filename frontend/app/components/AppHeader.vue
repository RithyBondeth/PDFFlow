<script setup lang="ts">
const route = useRoute()

const links = [
  { label: 'Tools', to: '/#tools' },
  { label: 'How it works', to: '/#lifecycle' },
  { label: 'API', to: '/api-docs' },
] as const

/**
 * Underlines where you are, the way Reahu's nav does.
 *
 * Section links only count as current when their hash is the one in the URL —
 * matching on the path alone lit up every hash link at once, since they all
 * point at the same page.
 */
function isCurrent(to: string) {
  const [path, hash] = to.split('#')
  if (hash) return route.path === '/' && route.hash === `#${hash}`
  return route.path === path
}
</script>

<template>
  <header class="sticky top-0 z-50 border-b border-hairline bg-canvas/85 backdrop-blur-xl">
    <div class="mx-auto flex h-16 max-w-6xl items-center gap-4 px-5 sm:px-6">
      <NuxtLink to="/" class="flex items-center gap-2.5" aria-label="PDFFlow home">
        <span class="flex size-7 items-center justify-center rounded-[5px] bg-accent-500 text-white">
          <UIcon name="i-lucide-layers" class="size-4" />
        </span>
        <span class="font-display text-[17px] tracking-tight">
          <span class="font-bold text-ink">PDF</span><span class="font-normal text-ink-faint">Flow</span>
        </span>
      </NuxtLink>

      <nav class="ml-6 hidden items-center gap-6 sm:flex" aria-label="Main">
        <NuxtLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="relative py-1 text-sm transition-colors duration-200"
          :class="isCurrent(link.to) ? 'text-ink' : 'text-ink-muted hover:text-ink'"
        >
          {{ link.label }}
          <span
            v-if="isCurrent(link.to)"
            class="absolute -bottom-0.5 left-0 right-0 h-0.5 rounded-full bg-accent-500"
            aria-hidden="true"
          />
        </NuxtLink>
      </nav>

      <div class="ml-auto flex items-center gap-2">
        <ThemeToggle />
        <UButton to="/#upload" color="primary" size="sm">Add a file</UButton>
      </div>
    </div>
  </header>
</template>
