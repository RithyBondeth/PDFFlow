<template>
  <UApp>
    <!-- `grain` lays a fixed film-grain overlay over the whole app. Flat dark
         fills are what make dark interfaces look cheap; the grain is most of
         the fix and costs one pseudo-element. -->
    <div class="grain flex min-h-screen flex-col">
      <AppHeader />
      <main class="flex-1">
        <NuxtPage />
      </main>
      <AppFooter />
    </div>
  </UApp>
</template>
