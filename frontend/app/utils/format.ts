/** Auto-imported by Nuxt from `app/utils`. */

export function formatBytes(bytes: number, decimals = 1): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  )
  const value = bytes / 1024 ** index
  return `${value.toFixed(index === 0 ? 0 : decimals)} ${units[index]}`
}

export function formatCountdown(target: Date | null): string {
  if (!target) return ''
  const seconds = Math.max(0, Math.round((target.getTime() - Date.now()) / 1000))
  if (seconds === 0) return 'expired'
  const minutes = Math.floor(seconds / 60)
  return minutes >= 1
    ? `${minutes} min ${String(seconds % 60).padStart(2, '0')} s`
    : `${seconds} s`
}

/**
 * How much of a file's life is already spent, 0–100, for the fuse rail.
 *
 * The API only sends the expiry, so the start is inferred from the server's
 * retention window (FILE_TTL_MINUTES, 30 by default). That makes the rail
 * exact for a fresh upload and never wrong by more than the request latency.
 */
export function burnPercent(target: Date | null, windowMinutes = 30): number {
  if (!target || windowMinutes <= 0) return 0
  const remaining = (target.getTime() - Date.now()) / 1000
  const total = windowMinutes * 60
  return Math.min(100, Math.max(0, ((total - remaining) / total) * 100))
}

export const FAMILY_ICONS: Record<string, string> = {
  pdf: 'i-lucide-file-text',
  image: 'i-lucide-image',
  office: 'i-lucide-file-type',
}
