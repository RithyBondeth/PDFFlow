import { describe, expect, it } from 'vitest'
import {
  createPagePlan,
  duplicatePage,
  movePage,
  removePage,
  rotatePage,
} from '~/utils/pageOrganizer'

describe('page organizer plan', () => {
  it('starts with every source page in document order', () => {
    expect(createPagePlan(3)).toEqual([
      { source: 1, rotation: 0 },
      { source: 2, rotation: 0 },
      { source: 3, rotation: 0 },
    ])
  })

  it('supports reordering, rotation and duplication without mutating the input', () => {
    const original = createPagePlan(3)
    const moved = movePage(original, 2, 0)
    const rotated = rotatePage(moved, 1)
    const duplicated = duplicatePage(rotated, 1)

    expect(original.map((page) => page.source)).toEqual([1, 2, 3])
    expect(duplicated).toEqual([
      { source: 3, rotation: 0 },
      { source: 1, rotation: 90 },
      { source: 1, rotation: 90 },
      { source: 2, rotation: 0 },
    ])
  })

  it('never removes the final output page', () => {
    expect(removePage(createPagePlan(1), 0)).toEqual([{ source: 1, rotation: 0 }])
    expect(removePage(createPagePlan(3), 1).map((page) => page.source)).toEqual([1, 3])
  })
})
