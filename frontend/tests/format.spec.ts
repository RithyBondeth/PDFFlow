import { describe, expect, it, vi } from 'vitest'
import { burnPercent, formatBytes, formatCountdown } from '~/utils/format'

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

describe('burnPercent', () => {
  it('is zero without a target', () => {
    expect(burnPercent(null)).toBe(0)
  })

  it('is zero for a file that has just arrived', () => {
    expect(burnPercent(new Date(Date.now() + 30 * 60_000))).toBeCloseTo(0, 1)
  })

  it('is half way through the window at 15 minutes left', () => {
    expect(burnPercent(new Date(Date.now() + 15 * 60_000))).toBeCloseTo(50, 1)
  })

  it('clamps to 100 once the deadline has passed', () => {
    expect(burnPercent(new Date(Date.now() - 5 * 60_000))).toBe(100)
  })

  it('clamps to 0 for an expiry beyond the window', () => {
    expect(burnPercent(new Date(Date.now() + 90 * 60_000))).toBe(0)
  })

  it('honours a non-default retention window', () => {
    expect(burnPercent(new Date(Date.now() + 5 * 60_000), 10)).toBeCloseTo(50, 1)
  })

  it('does not divide by a zero window', () => {
    expect(burnPercent(new Date(Date.now() + 60_000), 0)).toBe(0)
  })
})
