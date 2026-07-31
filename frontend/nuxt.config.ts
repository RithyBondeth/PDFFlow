// Where the full stack is reachable while running `nuxt dev`. Only nginx is
// published to the host, so this is the nginx port, not the API container's.
const devStackOrigin = process.env.NUXT_DEV_STACK_ORIGIN || 'http://localhost:8080'

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
      // Dark-only by design, so the class is fixed here rather than toggled at
      // runtime. Nuxt UI's `dark` variant resolves off `.dark` on an ancestor;
      // without it every component would style itself for a light page.
      htmlAttrs: { lang: 'en', class: 'dark' },
      title: 'PDFFlow — Fast, Private PDF Tools. No Signup Required.',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'Merge, split, compress and convert PDFs in your browser. No account, no tracking, files deleted automatically.',
        },
        { name: 'theme-color', content: '#0a0b11' },
        { name: 'color-scheme', content: 'dark' },
      ],
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    },
  },

  // No accounts and no personalisation means every page can be static HTML,
  // hydrated on the client only where a tool actually needs interactivity.
  nitro: {
    compressPublicAssets: true,

    // FastAPI serves the docs, and in the real deployment nginx routes them
    // there. `nuxt dev` runs the Nuxt app alone, so without this the header's
    // API link 404s on the dev server even though it works in production.
    // devProxy is dev-only — nginx still owns these paths once deployed.
    devProxy: {
      '/docs': { target: `${devStackOrigin}/docs`, changeOrigin: true },
      '/redoc': { target: `${devStackOrigin}/redoc`, changeOrigin: true },
      '/openapi.json': { target: `${devStackOrigin}/openapi.json`, changeOrigin: true },
    },
  },

  typescript: { strict: true, typeCheck: false },
})
