export function apiProxyTarget(internalBase: string, requestPath: string): string {
  const url = new URL(requestPath, 'http://pdfflow.local')

  if (url.pathname !== '/api' && !url.pathname.startsWith('/api/')) {
    throw new Error('Only API paths can be proxied')
  }

  const base = internalBase.replace(/\/$/, '')
  const suffix = url.pathname.slice('/api'.length)
  return `${base}${suffix}${url.search}`
}
