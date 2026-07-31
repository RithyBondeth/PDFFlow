/**
 * The sitemap, generated rather than checked in.
 *
 * A static public/sitemap.xml goes stale the moment a route is added or the
 * domain changes, and nothing fails loudly when it does. Building it from a
 * declared list next to the routes themselves keeps the two together, and lets
 * the origin come from runtime config so staging never advertises production
 * URLs.
 *
 * Only indexable pages belong here. /workspace is noindex, so listing it would
 * ask a crawler to fetch a page we then tell it to discard.
 */

interface SitemapEntry {
  path: string
  /** Relative to the others — Google treats this as a weak hint at best. */
  priority: string
  changefreq: string
}

const ENTRIES: SitemapEntry[] = [
  { path: '/', priority: '1.0', changefreq: 'weekly' },
  { path: '/api-docs', priority: '0.7', changefreq: 'monthly' },
]

export default defineEventHandler((event) => {
  const siteUrl = String(useRuntimeConfig().public.siteUrl).replace(/\/$/, '')
  const lastmod = new Date().toISOString().split('T')[0]

  const urls = ENTRIES.map(
    (entry) => `  <url>
    <loc>${siteUrl}${entry.path}</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>${entry.changefreq}</changefreq>
    <priority>${entry.priority}</priority>
  </url>`,
  ).join('\n')

  setHeader(event, 'content-type', 'application/xml; charset=utf-8')
  setHeader(event, 'cache-control', 'public, max-age=3600')

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`
})
