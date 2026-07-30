import type { Job, JobStatus } from '~/types/api'

interface StreamState {
  status: JobStatus
  progress: number
  stage: string | null
  errorMessage: string | null
  outputFilename: string | null
  outputSize: number | null
  result: Record<string, unknown>
}

const STAGE_LABELS: Record<string, string> = {
  queued: 'Waiting for a worker…',
  preparing: 'Preparing your document…',
  merging: 'Merging pages…',
  splitting: 'Splitting pages…',
  optimizing: 'Optimising…',
  writing: 'Generating result…',
  finishing: 'Almost done…',
  completed: 'Ready to download',
  failed: 'Processing failed',
}

/**
 * Follows a job over Server-Sent Events, falling back to polling if the
 * stream cannot be established (older proxies, restrictive networks).
 */
export function useJobStream() {
  const api = useApi()

  const state = reactive<StreamState>({
    status: 'pending',
    progress: 0,
    stage: 'queued',
    errorMessage: null,
    outputFilename: null,
    outputSize: null,
    result: {},
  })

  let source: EventSource | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null

  const label = computed(
    () => STAGE_LABELS[state.stage ?? ''] ?? 'Processing PDF…',
  )
  const isTerminal = computed(
    () => state.status === 'completed' || state.status === 'failed' || state.status === 'expired',
  )

  function apply(data: Record<string, any>) {
    if (data.status) state.status = data.status
    if (typeof data.progress === 'number') state.progress = data.progress
    if ('stage' in data) state.stage = data.stage
    if (data.errorMessage) state.errorMessage = data.errorMessage
    if (data.outputFilename) state.outputFilename = data.outputFilename
    if (typeof data.outputSize === 'number') state.outputSize = data.outputSize
    Object.assign(state.result, data)
  }

  function stop() {
    source?.close()
    source = null
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = null
  }

  function startPolling(jobId: string) {
    if (pollTimer) return
    pollTimer = setInterval(async () => {
      try {
        const job: Job = await api.getJob(jobId)
        apply(job as unknown as Record<string, unknown>)
        if (isTerminal.value) stop()
      } catch {
        stop()
      }
    }, 1500)
  }

  function start(jobId: string) {
    stop()
    Object.assign(state, {
      status: 'pending',
      progress: 0,
      stage: 'queued',
      errorMessage: null,
    })

    source = new EventSource(api.eventsUrl(jobId))
    for (const name of ['job_created', 'job_progress', 'job_completed', 'job_failed']) {
      source.addEventListener(name, (event) => {
        apply(JSON.parse((event as MessageEvent).data))
        if (isTerminal.value) stop()
      })
    }
    source.onerror = () => {
      // The browser retries SSE on its own, but if the connection never
      // succeeds we would spin silently — polling is the safe fallback.
      if (!isTerminal.value) startPolling(jobId)
    }
  }

  onScopeDispose(stop)

  return { state, label, isTerminal, start, stop }
}
