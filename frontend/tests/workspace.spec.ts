import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useWorkspaceStore } from '~/stores/workspace'
import type { Operation, UploadedFile } from '~/types/api'

function file(id: string, name: string, size = 1000): UploadedFile {
  return {
    id,
    originalName: name,
    size,
    mimeType: 'application/pdf',
    family: 'pdf',
    pageCount: 3,
    expiresAt: new Date(Date.now() + 30 * 60_000).toISOString(),
  }
}

const merge: Operation = {
  key: 'merge',
  name: 'Merge PDF',
  description: '',
  category: 'organize',
  accepts: ['pdf'],
  multiFile: true,
  minFiles: 2,
  outputExtension: '.pdf',
  implemented: true,
  optionsSchema: {},
}

const compress: Operation = { ...merge, key: 'compress', name: 'Compress PDF', multiFile: false, minFiles: 1 }

describe('workspace store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('starts empty', () => {
    const store = useWorkspaceStore()
    expect(store.hasFiles).toBe(false)
    expect(store.totalSize).toBe(0)
    expect(store.expiresAt).toBeNull()
  })

  it('records an upload and its available tools', () => {
    const store = useWorkspaceStore()
    store.setUpload([file('a', 'one.pdf', 100), file('b', 'two.pdf', 250)], [merge])

    expect(store.hasFiles).toBe(true)
    expect(store.totalSize).toBe(350)
    expect(store.operations).toHaveLength(1)
  })

  it('reports the earliest expiry across files', () => {
    const store = useWorkspaceStore()
    const soon = new Date(Date.now() + 60_000).toISOString()
    store.setUpload(
      [file('a', 'one.pdf'), { ...file('b', 'two.pdf'), expiresAt: soon }],
      [merge],
    )

    expect(store.expiresAt?.toISOString()).toBe(soon)
  })

  it('reorders files, which is the order merge uses', () => {
    const store = useWorkspaceStore()
    store.setUpload([file('a', 'a.pdf'), file('b', 'b.pdf'), file('c', 'c.pdf')], [merge])

    store.reorder(2, 0)

    expect(store.files.map((f) => f.id)).toEqual(['c', 'a', 'b'])
  })

  it('ignores a reorder with an out-of-range index', () => {
    const store = useWorkspaceStore()
    store.setUpload([file('a', 'a.pdf')], [merge])

    store.reorder(5, 0)

    expect(store.files.map((f) => f.id)).toEqual(['a'])
  })

  it('removes a file by id', () => {
    const store = useWorkspaceStore()
    store.setUpload([file('a', 'a.pdf'), file('b', 'b.pdf')], [merge])

    store.removeFile('a')

    expect(store.files.map((f) => f.id)).toEqual(['b'])
  })

  it('clears a single-file tool when several files remain selected', () => {
    const store = useWorkspaceStore()
    store.setUpload([file('a', 'a.pdf'), file('b', 'b.pdf'), file('c', 'c.pdf')], [compress])
    store.selectOperation(compress)

    store.removeFile('a')

    expect(store.selectedOperation).toBeNull()
  })

  it('resets options when the tool changes', () => {
    const store = useWorkspaceStore()
    store.setUpload([file('a', 'a.pdf')], [compress, merge])
    store.options = { level: 'high' }

    store.selectOperation(merge)

    expect(store.options).toEqual({})
  })

  it('reset returns to a blank session', () => {
    const store = useWorkspaceStore()
    store.setUpload([file('a', 'a.pdf')], [merge])
    store.jobId = 'job-1'

    store.reset()

    expect(store.hasFiles).toBe(false)
    expect(store.jobId).toBeNull()
    expect(store.operations).toEqual([])
  })

  it('pairs each upload with the browser file it came from', () => {
    const store = useWorkspaceStore()
    const first = new File(['%PDF-'], 'a.pdf')
    const second = new File(['%PDF-'], 'b.pdf')
    store.setUpload([file('a', 'a.pdf'), file('b', 'b.pdf')], [merge], [first, second])

    expect(store.localFile('a')).toBe(first)
    expect(store.localFile('b')).toBe(second)
    expect(store.localFile(undefined)).toBeNull()
  })

  it('pairs nothing when the counts disagree rather than guessing', () => {
    const store = useWorkspaceStore()
    store.setUpload([file('a', 'a.pdf'), file('b', 'b.pdf')], [merge], [new File([''], 'a.pdf')])

    expect(store.localFile('a')).toBeNull()
  })

  it('forgets local files when they are removed or the session resets', () => {
    const store = useWorkspaceStore()
    const local = [new File([''], 'a.pdf'), new File([''], 'b.pdf')]
    store.setUpload([file('a', 'a.pdf'), file('b', 'b.pdf')], [merge], local)

    store.removeFile('a')
    expect(store.localFile('a')).toBeNull()
    expect(store.localFile('b')).toBe(local[1])

    store.reset()
    expect(store.localFile('b')).toBeNull()
  })
})
