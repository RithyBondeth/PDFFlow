import { describe, expect, it, vi } from 'vitest'
import { createThumbnailQueue } from '~/utils/thumbnailQueue'

const flush = () => new Promise((resolve) => setTimeout(resolve, 0))

function backend(overrides: Partial<Parameters<typeof createThumbnailQueue>[0]> = {}) {
  let active = 0
  let peak = 0
  const fake = {
    open: vi.fn(async () => 'doc'),
    render: vi.fn(async (_doc: unknown, page: number) => {
      active += 1
      peak = Math.max(peak, active)
      await flush()
      active -= 1
      return `blob:page-${page}`
    }),
    close: vi.fn(),
    revoke: vi.fn(),
    ...overrides,
  }
  return { fake, peak: () => peak }
}

async function settle() {
  for (let i = 0; i < 10; i++) await flush()
}

describe('thumbnail queue', () => {
  it('renders requested pages one at a time, opening the document once', async () => {
    const { fake, peak } = backend()
    const ready = new Map<number, string>()
    const queue = createThumbnailQueue(fake, (page, url) => ready.set(page, url))

    queue.request(1)
    queue.request(3)
    queue.request(2)
    await settle()

    expect([...ready]).toEqual([[1, 'blob:page-1'], [3, 'blob:page-3'], [2, 'blob:page-2']])
    expect(fake.open).toHaveBeenCalledTimes(1)
    expect(peak()).toBe(1)
  })

  it('renders a page once however often it is requested', async () => {
    const { fake } = backend()
    const queue = createThumbnailQueue(fake, () => {})

    queue.request(2)
    queue.request(2)
    await settle()
    queue.request(2)
    await settle()

    expect(fake.render).toHaveBeenCalledTimes(1)
  })

  it('skips a page that fails and carries on with the rest', async () => {
    const { fake } = backend({
      render: vi.fn(async (_doc: unknown, page: number) => {
        if (page === 1) throw new Error('bad page')
        return `blob:page-${page}`
      }),
    })
    const ready: number[] = []
    const queue = createThumbnailQueue(fake, (page) => ready.push(page))

    queue.request(1)
    queue.request(2)
    await settle()

    expect(ready).toEqual([2])
  })

  it('gives up quietly when the document cannot be opened', async () => {
    const { fake } = backend({ open: vi.fn(async () => Promise.reject(new Error('not a pdf'))) })
    const unavailable = vi.fn()
    const queue = createThumbnailQueue(fake, () => {}, unavailable)

    queue.request(1)
    queue.request(2)
    await settle()

    expect(unavailable).toHaveBeenCalledTimes(1)
    expect(fake.render).not.toHaveBeenCalled()
  })

  it('revokes every URL and closes the document on dispose', async () => {
    const { fake } = backend()
    const queue = createThumbnailQueue(fake, () => {})

    queue.request(1)
    queue.request(2)
    await settle()
    queue.dispose()
    await settle()

    expect(fake.revoke.mock.calls.map(([url]) => url)).toEqual(['blob:page-1', 'blob:page-2'])
    expect(fake.close).toHaveBeenCalledWith('doc')
  })

  it('revokes a render that finishes after dispose instead of leaking it', async () => {
    const { fake } = backend()
    const ready = vi.fn()
    const queue = createThumbnailQueue(fake, ready)

    queue.request(1)
    await flush() // the render is now in flight
    queue.dispose()
    await settle()

    expect(ready).not.toHaveBeenCalled()
    expect(fake.revoke).toHaveBeenCalledWith('blob:page-1')
  })
})
