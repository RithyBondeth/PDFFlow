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

export const FAMILY_ICONS: Record<string, string> = {
  pdf: 'i-lucide-file-text',
  image: 'i-lucide-image',
  office: 'i-lucide-file-type',
}
