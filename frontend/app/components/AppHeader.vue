<template>
  <header class="sticky top-0 z-50 border-b border-ink-800/60 bg-ink-950/70 backdrop-blur-xl">
    <div class="mx-auto flex h-16 max-w-6xl items-center gap-3 px-6">
      <NuxtLink to="/" class="flex items-center gap-2 font-semibold text-ink-200">
        <span class="flex size-8 items-center justify-center rounded-lg bg-accent-500/15 text-accent-400">
          <UIcon name="i-lucide-file-stack" class="size-5" />
        </span>
        PDFFlow
      </NuxtLink>

      <UBadge color="neutral" variant="subtle" size="sm" class="hidden sm:inline-flex">
        No signup
      </UBadge>

      <nav class="ml-auto flex items-center gap-1 text-sm">
        <UButton to="/#tools" variant="ghost" color="neutral">Tools</UButton>
        <UButton to="/#privacy" variant="ghost" color="neutral">Privacy</UButton>
        <!-- Swagger UI is served by FastAPI, not Nuxt: `external` stops the
             router from trying to resolve /docs as a page and 404ing. -->
        <UButton
          to="/docs"
          external
          target="_blank"
          variant="ghost"
          color="neutral"
          class="hidden sm:inline-flex"
        >
          API
        </UButton>
      </nav>
    </div>
  </header>
</template>
