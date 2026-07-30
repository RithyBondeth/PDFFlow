<template>
  <header class="sticky top-0 z-50 border-b border-ink-800/60 bg-white/80 backdrop-blur-xl">
    <div class="mx-auto flex h-16 max-w-6xl items-center gap-6 px-6">
      <NuxtLink to="/" class="flex items-center gap-2.5">
        <span class="flex size-8 items-center justify-center rounded-md bg-accent-400 text-ink-950">
          <UIcon name="i-lucide-file-stack" class="size-5" />
        </span>
        <span class="text-lg tracking-tight">
          <span class="font-bold text-ink-950">PDF</span><span class="font-medium text-ink-400">Flow</span>
        </span>
      </NuxtLink>

      <span class="hidden items-center gap-1.5 rounded-full border border-ink-800 px-2.5 py-1 font-mono text-xs uppercase tracking-widest text-ink-400 sm:inline-flex">
        <span class="size-1.5 rounded-xs bg-accent-400" aria-hidden="true" />
        No signup
      </span>

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

      <UButton
        to="/#upload"
        color="primary"
        trailing-icon="i-lucide-arrow-right"
        class="font-medium"
      >
        Get started
      </UButton>
    </div>
  </header>
</template>
