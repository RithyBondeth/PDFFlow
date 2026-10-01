/**
 * Watermark geometry for the live preview.
 *
 * Mirrors backend/app/worker/operations/watermark_ops.py so the preview is
 * where the server will draw. Change both together. Units are PDF points on
 * the page as viewed (its own rotation already applied).
 */

export type WatermarkSize = 'small' | 'medium' | 'large'
export type WatermarkLayout = 'center' | 'tile'
export type WatermarkAngle = 0 | 45
export type WatermarkColor = 'gray' | 'red' | 'blue' | 'black'

export const WATERMARK_COLORS: Record<WatermarkColor, string> = {
  gray: 'rgb(115 115 115)',
  red: 'rgb(209 33 33)',
  blue: 'rgb(38 89 217)',
  black: 'rgb(0 0 0)',
}

const CENTER_SIZES: Record<WatermarkSize, number> = { small: 0.35, medium: 0.55, large: 0.75 }
const TILE_SIZES: Record<WatermarkSize, number> = { small: 0.14, medium: 0.2, large: 0.28 }
const MAX_TILES = 400

// Helvetica Bold's vertical metrics as PyMuPDF reports them.
export const FONT_ASCENDER = 1.07
export const FONT_DESCENDER = -0.307

export interface MarkSize {
  width: number
  height: number
  /** Font size for text marks. */
  fontSize?: number
}

export function span(width: number, height: number, angle: WatermarkAngle): number {
  return angle === 0 ? width : Math.min(width, height) * Math.SQRT2
}

export function targetWidth(
  page: { width: number; height: number },
  angle: WatermarkAngle,
  layout: WatermarkLayout,
  size: WatermarkSize,
): number {
  const share = (layout === 'center' ? CENTER_SIZES : TILE_SIZES)[size]
  return span(page.width, page.height, angle) * share
}

/**
 * `widthAtOnePoint` is the text's advance width at a font size of 1, which
 * the caller measures (the browser cannot read PyMuPDF's metrics directly).
 */
export function textMark(widthAtOnePoint: number, target: number, pageHeight: number): MarkSize {
  const raw = widthAtOnePoint > 0 ? target / widthAtOnePoint : 6
  const fontSize = Math.max(6, Math.min(raw, pageHeight * 0.3, 300))
  return {
    width: widthAtOnePoint * fontSize,
    height: fontSize * (FONT_ASCENDER - FONT_DESCENDER),
    fontSize,
  }
}

/** `aspect` is the image's height divided by its width. */
export function imageMark(aspect: number, target: number, pageHeight: number): MarkSize {
  let width = target
  let height = width * aspect
  if (height > pageHeight * 0.8) {
    height = pageHeight * 0.8
    width = height / aspect
  }
  return { width, height }
}

export function rotatedBox(width: number, height: number, angle: WatermarkAngle) {
  const rad = (angle * Math.PI) / 180
  const cos = Math.abs(Math.cos(rad))
  const sin = Math.abs(Math.sin(rad))
  return { width: width * cos + height * sin, height: width * sin + height * cos }
}

/** Centres of every mark: the page centre, or a staggered grid. */
export function positions(
  page: { width: number; height: number },
  box: { width: number; height: number },
  layout: WatermarkLayout,
): { x: number; y: number }[] {
  const cx = page.width / 2
  const cy = page.height / 2
  if (layout === 'center') return [{ x: cx, y: cy }]

  const gap = 0.5 * Math.min(box.width, box.height) + 18
  let stepX = box.width + gap
  let stepY = box.height + gap
  const grid = () => [Math.ceil(cy / stepY) + 1, Math.ceil(cx / stepX) + 1] as const
  let [rows, cols] = grid()
  // Keep pathological inputs (a single tiny character) bounded.
  while ((2 * rows + 1) * (2 * cols + 1) > MAX_TILES) {
    stepX *= 1.25
    stepY *= 1.25
    ;[rows, cols] = grid()
  }
  const points: { x: number; y: number }[] = []
  for (let row = -rows; row <= rows; row++) {
    const offset = row % 2 ? stepX / 2 : 0
    for (let col = -cols; col <= cols; col++) {
      points.push({ x: cx + col * stepX + offset, y: cy + row * stepY })
    }
  }
  return points
}
