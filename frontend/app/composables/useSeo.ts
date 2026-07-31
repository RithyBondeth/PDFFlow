/**
 * One place that decides what a page says about itself.
 *
 * Every indexable page needs the same six or seven tags, and the failure mode
 * when they drift is silent: a page keeps ranking under the wrong title, or a
 * shared link renders as a bare URL. Rather than repeat the list per page,
 * pages declare a title, a description and whether they should be indexed, and
 * this fills in the canonical, Open Graph and Twitter variants from those.
 */

interface SeoInput {
  /** The full <title>. Include the brand — there is no title template. */
  title: string
  description: string
  /** Path only, e.g. '/api-docs'. Defaults to the page being rendered. */
  path?: string
  /**
   * Keep the page out of the index. For app shells that have no meaning
   * without in-memory state — a crawler reaching them sees an empty room.
   */
  noindex?: boolean
}

export function useSeo(input: SeoInput) {
  const config = useRuntimeConfig()
  const route = useRoute()

  const siteUrl = String(config.public.siteUrl).replace(/\/$/, '')
  const url = `${siteUrl}${input.path ?? route.path}`
  const image = `${siteUrl}/og-image.png`

  useSeoMeta({
    title: input.title,
    description: input.description,

    // Absolute URLs throughout: crawlers and social scrapers resolve these
    // without a document base, so a relative path silently yields nothing.
    ogTitle: input.title,
    ogDescription: input.description,
    ogUrl: url,
    ogType: 'website',
    ogSiteName: 'PDFFlow',
    ogLocale: 'en_US',
    ogImage: image,
    ogImageWidth: 1200,
    ogImageHeight: 630,
    ogImageType: 'image/png',
    ogImageAlt: 'PDFFlow — fast, private PDF tools, no signup required.',

    twitterCard: 'summary_large_image',
    twitterTitle: input.title,
    twitterDescription: input.description,
    twitterImage: image,
    twitterImageAlt: 'PDFFlow — fast, private PDF tools, no signup required.',

    robots: input.noindex ? 'noindex, follow' : 'index, follow',
  })

  useHead({
    link: [{ rel: 'canonical', href: url }],
  })
}
