import { describe, expect, it, vi } from 'vitest'
import { formatBytes, formatCountdown } from '~/utils/format'

describe('formatBytes', () => {
  it.each([
    [0, '0 B'],
    [-5, '0 B'],
    [512, '512 B'],
    [1024, '1.0 KB'],
    [1536, '1.5 KB'],
    [1024 * 1024, '1.0 MB'],
    [104857600, '100.0 MB'],
    [1024 ** 3 * 2, '2.0 GB'],
  ])('formats %i as %s', (input, expected) => {
    expect(formatBytes(input)).toBe(expected)
  })

  it('caps at GB rather than inventing a unit', () => {
    expect(formatBytes(1024 ** 5)).toContain('GB')
  })

  it('survives a non-finite input', () => {
    expect(formatBytes(Number.NaN)).toBe('0 B')
  })
})

describe('formatCountdown', () => {
  it('is empty without a target', () => {
    expect(formatCountdown(null)).toBe('')
  })

  it('shows seconds under a minute', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'))
    expect(formatCountdown(new Date('2026-01-01T00:00:45Z'))).toBe('45 s')
    vi.useRealTimers()
  })

  it('shows minutes and zero-padded seconds above a minute', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'))
    expect(formatCountdown(new Date('2026-01-01T00:05:07Z'))).toBe('5 min 07 s')
    vi.useRealTimers()
  })

  it('says expired once the deadline has passed', () => {
    expect(formatCountdown(new Date(Date.now() - 10_000))).toBe('expired')
  })
})
