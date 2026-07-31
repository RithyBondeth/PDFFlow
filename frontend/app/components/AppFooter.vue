<template>
  <footer class="mt-8 border-t border-hairline">
    <div class="reveal mx-auto max-w-6xl px-5 py-20 text-center sm:px-6">
      <p class="eyebrow">Nothing to sign up for</p>
      <h2
        class="font-display mx-auto mt-5 max-w-xl text-balance text-4xl font-bold leading-[1.02] tracking-[-0.025em] text-ink sm:text-5xl"
      >
        Bring a file.<br>
        <span class="mark">Leave with a file.</span>
      </h2>
      <p class="mx-auto mt-5 max-w-md text-pretty text-ink-muted">
        Everything in between happens on our server and then stops existing.
      </p>
      <div class="mt-8">
        <UButton to="/#upload" color="primary" size="lg" trailing-icon="i-lucide-arrow-right">
          Add a file
        </UButton>
      </div>
    </div>

    <div class="border-t border-hairline py-8">
      <div
        class="mx-auto flex max-w-6xl flex-col items-center gap-3 px-5 text-center sm:flex-row sm:justify-between sm:px-6 sm:text-left"
      >
        <p class="font-data text-xs text-ink-faint">
          © {{ new Date().getFullYear() }} PDFFlow — no accounts, no tracking, no
          permanent storage.
        </p>
        <NuxtLink
          to="/api-docs"
          class="font-data text-xs text-ink-faint underline decoration-hairline-strong underline-offset-4 transition-colors hover:text-accent-ink"
        >
          API reference
        </NuxtLink>
      </div>
    </div>
  </footer>
</template>
