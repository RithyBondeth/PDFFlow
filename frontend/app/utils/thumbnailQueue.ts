/**
 * Renders page thumbnails one at a time, on request, and caches them.
 *
 * Kept free of pdf.js and Vue so the scheduling rules can be tested on their
 * own: the organiser can show up to 1000 cards, and rendering all of them up
 * front (or all at once) would stall the tab on a large document.
 */
export interface ThumbnailBackend<Doc> {
  open: () => Promise<Doc>
  /** Returns an object URL for the 1-based page. */
  render: (doc: Doc, page: number) => Promise<string>
  close: (doc: Doc) => void
  revoke: (url: string) => void
}

export interface ThumbnailQueue {
  /** Ask for a page. Repeated and concurrent requests are coalesced. */
  request: (page: number) => void
  /** Release the document and every URL handed out. */
  dispose: () => void
}

export function createThumbnailQueue<Doc>(
  backend: ThumbnailBackend<Doc>,
  onReady: (page: number, url: string) => void,
  onUnavailable: () => void = () => {},
): ThumbnailQueue {
  const queue: number[] = []
  const known = new Set<number>()
  const urls: string[] = []
  let doc: Promise<Doc | null> | null = null
  let running = false
  let disposed = false
  let broken = false

  function document(): Promise<Doc | null> {
    doc ??= backend.open().catch(() => {
      // A file pdf.js cannot open will not get better on retry. The cards
      // keep their plain placeholder; the server still validates the PDF.
      broken = true
      onUnavailable()
      return null
    })
    return doc
  }

  async function pump() {
    if (running) return
    running = true
    try {
      while (queue.length && !disposed && !broken) {
        const page = queue.shift()!
        const opened = await document()
        if (!opened || disposed) break
        try {
          const url = await backend.render(opened, page)
          if (disposed) {
            backend.revoke(url)
            break
          }
          urls.push(url)
          onReady(page, url)
        } catch {
          // One unrenderable page should not take the others down with it.
        }
      }
    } finally {
      running = false
    }
  }

  return {
    request(page) {
      if (disposed || broken || known.has(page)) return
      known.add(page)
      queue.push(page)
      void pump()
    },
    dispose() {
      disposed = true
      queue.length = 0
      urls.splice(0).forEach(backend.revoke)
      void doc?.then((opened) => opened && backend.close(opened))
    },
  }
}
