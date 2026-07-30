/**
 * Nuxt auto-imports the Vue reactivity API into every file. Outside the Nuxt
 * runtime those globals do not exist, so the store and composables under test
 * get them here.
 */
import * as vue from 'vue'

const AUTO_IMPORTED = [
  'ref',
  'computed',
  'reactive',
  'watch',
  'watchEffect',
  'onScopeDispose',
  'onMounted',
  'toRef',
  'toRefs',
  'nextTick',
] as const

for (const name of AUTO_IMPORTED) {
  ;(globalThis as Record<string, unknown>)[name] = (vue as Record<string, unknown>)[name]
}
