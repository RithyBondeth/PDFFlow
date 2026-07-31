<template>
  <UApp>
    <GridBackdrop />

    <!-- z-10 keeps the whole app above the backdrop layer. -->
    <div class="relative z-10 flex min-h-screen flex-col">
      <AppHeader />
      <main class="flex-1">
        <NuxtPage />
      </main>
      <AppFooter />
    </div>
  </UApp>
</template>
