import { defineStore } from 'pinia'
import type { Operation, UploadedFile } from '~/types/api'

/**
 * Holds the current, deliberately ephemeral session: the files the user just
 * uploaded and the tool they picked. Nothing is persisted — reloading the page
 * genuinely starts over, which matches what the server does.
 */
export const useWorkspaceStore = defineStore('workspace', () => {
  const files = ref<UploadedFile[]>([])
  const operations = ref<Operation[]>([])
  const selectedOperation = ref<Operation | null>(null)
  const options = ref<Record<string, unknown>>({})
  const jobId = ref<string | null>(null)
  const error = ref<string | null>(null)
  // The browser's own copy of each upload, keyed by server file id, so pages
  // can be previewed locally without asking the server for anything. Held as
  // a plain Map: File objects gain nothing from being made reactive.
  const localFiles = shallowRef(new Map<string, File>())

  const hasFiles = computed(() => files.value.length > 0)
  const totalSize = computed(() =>
    files.value.reduce((sum, file) => sum + file.size, 0),
  )
  const expiresAt = computed(() =>
    files.value.length
      ? new Date(
          Math.min(...files.value.map((f) => new Date(f.expiresAt).getTime())),
        )
      : null,
  )

  /**
   * `local` is the list that was sent to /upload. The API answers in the same
   * order, which is what lets each server id be paired with its source File.
   */
  function setUpload(uploaded: UploadedFile[], available: Operation[], local: File[] = []) {
    files.value = uploaded
    localFiles.value = new Map(
      local.length === uploaded.length
        ? uploaded.map((file, index) => [file.id, local[index]!] as const)
        : [],
    )
    operations.value = available
    selectedOperation.value = null
    options.value = {}
    jobId.value = null
    error.value = null
  }

  function removeFile(id: string) {
    files.value = files.value.filter((file) => file.id !== id)
    if (localFiles.value.has(id)) {
      const next = new Map(localFiles.value)
      next.delete(id)
      localFiles.value = next
    }
    if (selectedOperation.value && !selectedOperation.value.multiFile && files.value.length > 1) {
      selectedOperation.value = null
    }
  }

  /** Drag-and-drop reordering; merge uses this order verbatim. */
  function reorder(from: number, to: number) {
    const next = [...files.value]
    const [moved] = next.splice(from, 1)
    if (moved) next.splice(to, 0, moved)
    files.value = next
  }

  function selectOperation(operation: Operation) {
    selectedOperation.value = operation
    options.value = {}
  }

  function localFile(id: string | undefined): File | null {
    return (id && localFiles.value.get(id)) || null
  }

  function reset() {
    files.value = []
    localFiles.value = new Map()
    operations.value = []
    selectedOperation.value = null
    options.value = {}
    jobId.value = null
    error.value = null
  }

  return {
    files,
    operations,
    selectedOperation,
    options,
    jobId,
    error,
    hasFiles,
    totalSize,
    expiresAt,
    setUpload,
    localFile,
    removeFile,
    reorder,
    selectOperation,
    reset,
  }
})
