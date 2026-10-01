import { describe, expect, it } from 'vitest'
import {
  imageMark,
  positions,
  rotatedBox,
  span,
  targetWidth,
  textMark,
} from '~/utils/watermarkLayout'

// Reference values computed by backend/app/worker/operations/watermark_ops.py.
// If the server's layout changes, regenerate them there and update both.
describe('watermark layout mirrors the server', () => {
  it('measures the span a mark may run along', () => {
    expect(span(595, 842, 0)).toBe(595)
    expect(span(595, 842, 45)).toBeCloseTo(841.4571, 3)
  })

  it('sizes the rotated bounding box', () => {
    const box = rotatedBox(300, 60, 45)
    expect(box.width).toBeCloseTo(254.5584, 3)
    expect(box.height).toBeCloseTo(254.5584, 3)
  })

  it('lays out the same tile grid', () => {
    const points = positions({ width: 595, height: 842 }, { width: 120, height: 50 }, 'tile')
    expect(points).toHaveLength(91)
    expect(points[0]!.x).toBeCloseTo(-191.5, 3)
    expect(points[0]!.y).toBeCloseTo(-137, 3)
    expect(points[13]!.x).toBeCloseTo(868, 3)
    expect(points[13]!.y).toBeCloseTo(-44, 3)
  })

  it('caps the tile count for tiny marks the same way', () => {
    expect(positions({ width: 595, height: 842 }, { width: 2, height: 2 }, 'tile')).toHaveLength(315)
  })

  it('centres a single mark', () => {
    expect(positions({ width: 595, height: 842 }, { width: 10, height: 10 }, 'center')).toEqual([
      { x: 297.5, y: 421 },
    ])
  })
})

describe('mark sizing', () => {
  const a4 = { width: 595, height: 842 }

  it('scales text to the share of the span for its size', () => {
    const target = targetWidth(a4, 0, 'center', 'medium')
    expect(target).toBeCloseTo(595 * 0.55, 6)
    const mark = textMark(5, target, a4.height)
    expect(mark.width).toBeCloseTo(target, 6)
  })

  it('stops very short text from becoming enormous', () => {
    const mark = textMark(0.7, targetWidth(a4, 0, 'center', 'large'), a4.height)
    expect(mark.fontSize).toBeCloseTo(842 * 0.3, 6)
  })

  it('keeps a tall image inside the page', () => {
    const mark = imageMark(4, 400, a4.height)
    expect(mark.height).toBeCloseTo(842 * 0.8, 6)
    expect(mark.width).toBeCloseTo((842 * 0.8) / 4, 6)
  })
})
