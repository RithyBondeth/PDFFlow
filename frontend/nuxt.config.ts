// Where the full stack is reachable while running `nuxt dev`. Only nginx is
// published to the host, so this is the nginx port, not the API container's.
const devStackOrigin = process.env.NUXT_DEV_STACK_ORIGIN || 'http://localhost:8080'

export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: true },

  modules: ['@nuxt/ui', '@pinia/nuxt', '@vueuse/nuxt'],

  // `/api` belongs to FastAPI at the reverse proxy. Nuxt Icon's default
  // fallback endpoint lives there too, which made every icon request miss the
  // frontend in production even when the collection was bundled locally.
  icon: {
    localApiEndpoint: '/_nuxt_icon',
  },

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

      // Canonical, Open Graph and sitemap URLs have to be absolute, and the
      // app cannot infer its own public origin from behind a proxy. Set
      // NUXT_PUBLIC_SITE_URL per environment; the default is production.
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL || 'https://pdfflow.bondeth.site',
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
        // One per scheme, so the browser chrome follows whichever the visitor
        // is actually in.
        {
          name: 'theme-color',
          content: '#ffffff',
          media: '(prefers-color-scheme: light)',
        },
        {
          name: 'theme-color',
          content: '#1a1b1e',
          media: '(prefers-color-scheme: dark)',
        },
        { name: 'color-scheme', content: 'light dark' },
      ],
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg?v=2' }],
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
