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

  function setUpload(uploaded: UploadedFile[], available: Operation[]) {
    files.value = uploaded
    operations.value = available
    selectedOperation.value = null
    options.value = {}
    jobId.value = null
    error.value = null
  }

  function removeFile(id: string) {
    files.value = files.value.filter((file) => file.id !== id)
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

  function reset() {
    files.value = []
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
    removeFile,
    reorder,
    selectOperation,
    reset,
  }
})
