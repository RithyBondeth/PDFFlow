import type { Job, Operation, UploadResponse } from '~/types/api'

/**
 * Thin wrapper around the PDFFlow API.
 *
 * Every failure is normalised into an `Error` carrying the server's
 * user-facing message, so components never have to inspect status codes.
 */
export function useApi() {
  const config = useRuntimeConfig()

  // Browser-facing URLs always use the public base: they are either fetched by
  // the browser or embedded in rendered HTML, so an internal hostname would be
  // unreachable for the user.
  const publicBase = config.public.apiBase
  // Server-rendered fetches go direct to the API container.
  const base = import.meta.server ? config.apiInternal : publicBase

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response: Response
    try {
      response = await fetch(`${base}${path}`, init)
    } catch {
      throw new Error('Could not reach PDFFlow. Check your connection.')
    }

    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new Error(
        body?.error?.message ?? 'Something went wrong. Please try again.',
      )
    }
    return response.json() as Promise<T>
  }

  /** Uploads with real progress, which `fetch` still cannot report. */
  function upload(
    files: File[],
    onProgress?: (percent: number) => void,
    signal?: AbortSignal,
  ): Promise<UploadResponse> {
    const form = new FormData()
    files.forEach((file) => form.append('files', file, file.name))

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${publicBase}/upload`)
      xhr.responseType = 'json'

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          onProgress?.(Math.round((event.loaded / event.total) * 100))
        }
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.response as UploadResponse)
        } else {
          reject(
            new Error(
              xhr.response?.error?.message ??
                'Upload failed. Please try again.',
            ),
          )
        }
      }
      xhr.onerror = () => reject(new Error('Upload failed. Please try again.'))
      xhr.onabort = () => reject(new Error('Upload cancelled.'))
      signal?.addEventListener('abort', () => xhr.abort())

      xhr.send(form)
    })
  }

  return {
    upload,
    operations: () => request<Operation[]>('/operations'),
    createJob: (operation: string, fileIds: string[], options: Record<string, unknown> = {}) =>
      request<Job>('/jobs/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation, fileIds, options }),
      }),
    getJob: (id: string) => request<Job>(`/jobs/${id}`),
    downloadUrl: (id: string) => `${publicBase}/download/${id}`,
    eventsUrl: (id: string) => `${publicBase}/jobs/${id}/events`,
  }
}
