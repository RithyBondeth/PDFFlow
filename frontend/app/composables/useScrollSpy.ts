/**
 * Picks which of the currently-visible sections counts as "being read": the one
 * nearest the top of the reading area.
 *
 * Split out from the observer so it can be tested without a layout engine —
 * whichever heading is highest wins, so scrolling up highlights the section
 * coming back into view rather than whichever entry happened to fire last.
 */
export function topmostVisible(visible: Map<string, number>): string | null {
  let bestId: string | null = null
  let bestTop = Number.POSITIVE_INFINITY

  for (const [id, top] of visible) {
    if (top < bestTop) {
      bestTop = top
      bestId = id
    }
  }
  return bestId
}

/**
 * Tracks which section is currently being read, for the reference sidebar.
 *
 * Uses IntersectionObserver rather than scroll maths so it stays cheap on a very
 * long page. The top margin matches the sticky header's height, so a heading
 * only counts as current once it has cleared the chrome. Where the API is
 * missing the sidebar simply never highlights — the links still work.
 */
export function useScrollSpy(ids: MaybeRefOrGetter<string[]>) {
  const active = ref<string | null>(null)
  let observer: IntersectionObserver | null = null

  function connect() {
    observer?.disconnect()
    if (typeof IntersectionObserver === 'undefined') return

    const visible = new Map<string, number>()

    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) visible.set(entry.target.id, entry.boundingClientRect.top)
          else visible.delete(entry.target.id)
        }
        const next = topmostVisible(visible)
        if (next) active.value = next
      },
      { rootMargin: '-72px 0px -55% 0px', threshold: 0 },
    )

    for (const id of toValue(ids)) {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    }
  }

  /**
   * Seed from the URL so a clicked link or a shared deep link highlights at
   * once, without waiting for the observer's first callback. It also means the
   * sidebar still tracks navigation where IntersectionObserver never reports —
   * a headless renderer, or a tab that is never composited.
   */
  function syncFromHash() {
    const id = window.location.hash.slice(1)
    if (id && toValue(ids).includes(id)) active.value = id
  }

  onMounted(() => {
    syncFromHash()
    connect()
  })

  // Re-observe if the tracked set changes (it does not today, but a stale
  // observer silently stops updating and that is a miserable bug to find).
  watch(() => toValue(ids), connect, { flush: 'post' })

  if (import.meta.client) {
    useEventListener(window, 'hashchange', syncFromHash)
  }

  onScopeDispose(() => observer?.disconnect())

  return { active }
}
