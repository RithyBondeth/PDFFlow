<template>
  <footer class="mt-8 border-t border-line/80">
    <div class="reveal mx-auto max-w-6xl px-5 py-20 text-center sm:px-6">
      <p class="eyebrow">Nothing to sign up for</p>
      <h2
        class="font-display mx-auto mt-5 max-w-xl text-balance text-4xl font-extrabold leading-[1.05] tracking-tight text-paper sm:text-5xl"
      >
        Bring a file. Leave with a file.
      </h2>
      <p class="mx-auto mt-4 max-w-md text-pretty text-paper-dim">
        Everything in between happens on our server and then stops existing.
      </p>
      <div class="mt-8">
        <UButton
          to="/#upload"
          color="primary"
          size="lg"
          trailing-icon="i-lucide-arrow-right"
          class="shadow-[0_0_36px_-8px_oklch(0.772_0.155_76/0.6)] hover:-translate-y-0.5 hover:shadow-[0_0_44px_-6px_oklch(0.772_0.155_76/0.75)]"
        >
          Add a file
        </UButton>
      </div>
    </div>

    <div class="border-t border-line/60 py-8">
      <div
        class="mx-auto flex max-w-6xl flex-col items-center gap-3 px-5 text-center sm:flex-row sm:justify-between sm:px-6 sm:text-left"
      >
        <p class="font-data text-xs text-paper-faint">
          © {{ new Date().getFullYear() }} PDFFlow — no accounts, no tracking, no
          permanent storage.
        </p>
        <NuxtLink
          to="/docs"
          external
          target="_blank"
          class="font-data text-xs text-paper-faint underline decoration-line-lit underline-offset-4 transition-colors hover:text-accent-300"
        >
          API reference
        </NuxtLink>
      </div>
    </div>
  </footer>
</template>
