import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

// A plain Vitest setup rather than `@nuxt/test-utils`' Nuxt environment, which
// does not currently boot under Vitest 3. These tests therefore cover the
// framework-independent logic — formatting, the workspace store, job-stream
// state — where the real risk of regression is. Component rendering is left to
// the type checker and the build.
export default defineConfig({
  resolve: {
    alias: {
      '~': fileURLToPath(new URL('./app', import.meta.url)),
      '@': fileURLToPath(new URL('./app', import.meta.url)),
    },
  },
  test: {
    environment: 'happy-dom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.spec.ts'],
  },
})
