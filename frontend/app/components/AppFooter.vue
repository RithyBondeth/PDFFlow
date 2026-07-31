<template>
  <footer class="border-t border-ink-800/60">
    <div class="reveal mx-auto max-w-6xl px-6 py-16 text-center">
      <span class="inline-flex items-center gap-1.5 rounded-full border border-ink-800 px-2.5 py-1 font-mono text-xs uppercase tracking-widest text-ink-400">
        <span class="size-1.5 rounded-xs bg-accent-400" aria-hidden="true" />
        No accounts. No catch.
      </span>
      <h2 class="mx-auto mt-5 max-w-lg text-balance text-3xl font-bold tracking-tight text-ink-950 sm:text-4xl">
        Your files, never stored.
      </h2>
      <div class="mt-7">
        <UButton
          to="/#upload"
          color="primary"
          size="lg"
          trailing-icon="i-lucide-arrow-right"
          class="font-medium transition-transform duration-200 hover:scale-105 active:scale-95"
        >
          Start with a file
        </UButton>
      </div>
    </div>

    <div class="border-t border-ink-800/60 py-8">
      <div class="mx-auto flex max-w-6xl flex-col items-center gap-2 px-6 text-center text-sm text-ink-400">
        <p>
          PDFFlow processes your files on the server and deletes them
          automatically. No accounts, no tracking, no permanent storage.
        </p>
        <p class="text-xs">© {{ new Date().getFullYear() }} PDFFlow</p>
      </div>
    </div>
  </footer>
</template>
