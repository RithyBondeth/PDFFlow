export type PageRotation = 0 | 90 | 180 | 270

export interface OrganizedPage {
  source: number
  rotation: PageRotation
}

export function createPagePlan(pageCount: number): OrganizedPage[] {
  if (!Number.isSafeInteger(pageCount) || pageCount < 1) return []
  return Array.from({ length: pageCount }, (_, index) => ({
    source: index + 1,
    rotation: 0,
  }))
}

export function movePage(
  pages: OrganizedPage[],
  from: number,
  to: number,
): OrganizedPage[] {
  if (from === to || from < 0 || from >= pages.length || to < 0 || to >= pages.length) {
    return [...pages]
  }
  const next = [...pages]
  const [moved] = next.splice(from, 1)
  if (moved) next.splice(to, 0, moved)
  return next
}

export function rotatePage(pages: OrganizedPage[], index: number): OrganizedPage[] {
  return pages.map((page, position) =>
    position === index
      ? { ...page, rotation: ((page.rotation + 90) % 360) as PageRotation }
      : page,
  )
}

export function duplicatePage(pages: OrganizedPage[], index: number): OrganizedPage[] {
  const page = pages[index]
  if (!page || pages.length >= 1000) return [...pages]
  const next = [...pages]
  next.splice(index + 1, 0, { ...page })
  return next
}

export function removePage(pages: OrganizedPage[], index: number): OrganizedPage[] {
  if (pages.length <= 1 || index < 0 || index >= pages.length) return [...pages]
  return pages.filter((_, position) => position !== index)
}
