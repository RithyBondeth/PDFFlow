import { describe, expect, it } from 'vitest'
import { fallbackOperations } from '~/data/operationCatalog'

describe('homepage operation catalog fallback', () => {
  it('keeps every public tool visible when the API is unavailable', () => {
    expect(fallbackOperations).toHaveLength(13)
    expect(fallbackOperations.filter((operation) => operation.implemented)).toHaveLength(5)
    expect(new Set(fallbackOperations.map((operation) => operation.key)).size).toBe(13)
  })

  it('covers every homepage category', () => {
    expect(new Set(fallbackOperations.map((operation) => operation.category))).toEqual(
      new Set(['organize', 'optimize', 'convert', 'security', 'edit']),
    )
  })
})
