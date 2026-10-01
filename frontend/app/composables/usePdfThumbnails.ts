import type { PDFDocumentProxy } from 'pdfjs-dist'
import type { ThumbnailQueue } from '~/utils/thumbnailQueue'
import { createThumbnailQueue } from '~/utils/thumbnailQueue'

// CSS width of a card's preview area at its widest. Rendering at this times
// the device pixel ratio (capped) keeps thumbnails crisp without paying for
// full-resolution pages.
const THUMBNAIL_CSS_WIDTH = 220
const MAX_PIXEL_RATIO = 2

/**
 * Page previews for a PDF the browser already holds.
 *
 * Everything happens locally: the File is the one the user picked, pdf.js
 * runs in a worker, and the results are object URLs that never leave the
 * tab. Nothing about the document is sent anywhere to draw these.
 */
export function usePdfThumbnails(file: MaybeRefOrGetter<File | null>) {
  const thumbnails = shallowReactive(new Map<number, string>())
  const unavailable = ref(false)
  let queue: ThumbnailQueue | null = null

  function reset() {
    queue?.dispose()
    queue = null
    thumbnails.clear()
    unavailable.value = false
  }

  function start(source: File) {
    queue = createThumbnailQueue<PDFDocumentProxy>(
      {
        open: () => openDocument(source),
        render: renderPage,
        close: (doc) => void doc.destroy(),
        revoke: (url) => URL.revokeObjectURL(url),
      },
      (page, url) => thumbnails.set(page, url),
      () => (unavailable.value = true),
    )
  }

  watch(
    () => toValue(file),
    (source) => {
      reset()
      // pdf.js needs a DOM and a worker; there is nothing to do during SSR.
      if (source && import.meta.client) start(source)
    },
    { immediate: true },
  )
  onScopeDispose(reset)

  return {
    thumbnails,
    unavailable: readonly(unavailable),
    request: (page: number) => queue?.request(page),
  }
}

async function openDocument(source: File): Promise<PDFDocumentProxy> {
  // Loaded on first use: pdf.js is large, and only Organize Pages needs it.
  const [pdfjs, { default: workerUrl }] = await Promise.all([
    import('pdfjs-dist'),
    import('pdfjs-dist/build/pdf.worker.min.mjs?url'),
  ])
  pdfjs.GlobalWorkerOptions.workerSrc = workerUrl
  return pdfjs.getDocument({
    data: new Uint8Array(await source.arrayBuffer()),
    // Hardening for untrusted input: no eval-compiled font code, no
    // document scripting, and no fetching of anything the PDF points at.
    isEvalSupported: false,
    enableXfa: false,
    disableAutoFetch: true,
    disableStream: true,
  }).promise
}

async function renderPage(doc: PDFDocumentProxy, pageNumber: number): Promise<string> {
  const page = await doc.getPage(pageNumber)
  try {
    // getViewport applies the page's own /Rotate, so the preview matches what
    // the server will start from; the organiser's rotation is added in CSS.
    const natural = page.getViewport({ scale: 1 })
    const ratio = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO)
    const viewport = page.getViewport({
      scale: (THUMBNAIL_CSS_WIDTH * ratio) / Math.max(natural.width, natural.height),
    })

    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.floor(viewport.width))
    canvas.height = Math.max(1, Math.floor(viewport.height))
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Canvas is not available')
    // Transparent pages would show the card colour through; paper is white.
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, canvas.width, canvas.height)

    await page.render({ canvasContext: context, viewport }).promise

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/webp', 0.85),
    )
    if (!blob) throw new Error('Could not encode the thumbnail')
    return URL.createObjectURL(blob)
  } finally {
    page.cleanup()
  }
}
