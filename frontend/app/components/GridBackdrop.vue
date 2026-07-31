<template>
  <!-- Graph-paper ruling behind the whole app, with one slow accent wash
       drifting over it.

       Fixed and inert: aria-hidden and pointer-events-none, so it is invisible
       to assistive tech and never intercepts a click. It sits at z-index 0 with
       the app content at z-index 10 — a negative z-index would paint it behind
       the body's own background colour and disappear entirely. -->
  <div class="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden="true">
    <div class="grid-rule absolute inset-0" />
    <div class="grid-beam beam-drift absolute inset-0" />
  </div>
</template>
