export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: true },

  modules: ['@nuxt/ui', '@pinia/nuxt', '@vueuse/nuxt'],

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    // Server-only. Relative URLs have no origin during SSR, so server-side
    // fetches must address the API container directly. Never exposed to the
    // browser, which reaches the same API through nginx on the public base.
    apiInternal: process.env.NUXT_API_INTERNAL || 'http://api:8000/api',

    public: {
      // Behind nginx the API is same-origin, so a relative base is correct in
      // production. `nuxt dev` overrides it via NUXT_PUBLIC_API_BASE.
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api',
    },
  },

  app: {
    head: {
      htmlAttrs: { lang: 'en' },
      title: 'PDFFlow — Fast, Private PDF Tools. No Signup Required.',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'Merge, split, compress and convert PDFs in your browser. No account, no tracking, files deleted automatically.',
        },
        { name: 'theme-color', content: '#0b0d12' },
      ],
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    },
  },

  // No accounts and no personalisation means every page can be static HTML,
  // hydrated on the client only where a tool actually needs interactivity.
  nitro: {
    compressPublicAssets: true,
  },

  typescript: { strict: true, typeCheck: false },
})
