/**
 * Tracks the pointer inside an element and publishes its position as the
 * `--mx` / `--my` custom properties the `.spotlight` class paints its amber
 * pool at.
 *
 * Writing the properties directly on the node rather than through reactive
 * style bindings is deliberate: pointermove fires on every frame, and going
 * via Vue's reactivity would queue a component re-render for each one.
 */
export function useSpotlight() {
  function track(event: PointerEvent) {
    const el = event.currentTarget as HTMLElement | null
    if (!el) return

    const box = el.getBoundingClientRect()
    el.style.setProperty('--mx', `${event.clientX - box.left}px`)
    el.style.setProperty('--my', `${event.clientY - box.top}px`)
  }

  return { track }
}
