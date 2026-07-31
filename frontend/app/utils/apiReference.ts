/**
 * The content of the API reference page.
 *
 * Kept as data rather than markup so the page, the sidebar and the drift test
 * all read from one place. The API itself is the source of truth: every path,
 * field and error code here was taken from backend/app/api/routes and
 * app/schemas/job.py, and tests/api-reference.spec.ts compares this list
 * against a live /openapi.json when one is reachable.
 */

/** Host used in the copyable examples. Swap for your own deployment. */
export const EXAMPLE_HOST = 'https://pdfflow.bondeth.site'

export interface DocField {
  name: string
  type: string
  /** Shown as a muted "optional"/"nullable" marker rather than prose. */
  note?: string
  description: string
}

export interface DocSample {
  label: string
  language: 'bash' | 'json' | 'http'
  code: string
}

export interface DocEndpoint {
  id: string
  method: 'GET' | 'POST'
  path: string
  summary: string
  description: string
  group: string
  /** Rate limit as advertised by the app-layer limiter, if any. */
  rateLimit?: string
  pathParams?: DocField[]
  body?: { contentType: string; fields: DocField[] }
  responds: { status: string; description: string }
  returns?: DocField[]
  samples: DocSample[]
  errors?: string[]
}

export interface DocGroup {
  id: string
  label: string
  blurb: string
}

export const GROUPS: DocGroup[] = [
  { id: 'files', label: 'Files', blurb: 'Get bytes into temporary storage' },
  { id: 'tools', label: 'Tools', blurb: 'What the worker can actually do' },
  { id: 'jobs', label: 'Jobs', blurb: 'Queue work and follow it' },
  { id: 'result', label: 'Result', blurb: 'Collect the output' },
  { id: 'system', label: 'System', blurb: 'Health and client limits' },
]

export const ENDPOINTS: DocEndpoint[] = [
  {
    id: 'post-upload',
    method: 'POST',
    path: '/api/upload',
    group: 'files',
    summary: 'Upload one or more files',
    description:
      'Sends files into temporary storage. Each one is written under a generated UUID name — the name you supply is kept only for display and never used on disk. The response also tells you which tools can run on what you just sent, so you never have to guess.',
    rateLimit: '30 requests / minute',
    body: {
      contentType: 'multipart/form-data',
      fields: [
        {
          name: 'files',
          type: 'file',
          note: 'repeatable, max 25',
          description:
            'One form field per file. PDF, JPEG, PNG, WebP, DOCX, XLSX and PPTX are accepted, up to 100 MB each.',
        },
      ],
    },
    responds: { status: '200', description: 'Files stored' },
    returns: [
      { name: 'files[].id', type: 'uuid', description: 'Pass this to /api/jobs/create.' },
      { name: 'files[].originalName', type: 'string', description: 'Sanitised display name.' },
      { name: 'files[].size', type: 'integer', description: 'Bytes as stored.' },
      { name: 'files[].mimeType', type: 'string', description: 'Resolved from the content, not the extension.' },
      { name: 'files[].family', type: 'string', description: 'One of pdf, image, office.' },
      { name: 'files[].pageCount', type: 'integer', note: 'nullable', description: 'Present for PDFs once counted.' },
      { name: 'files[].expiresAt', type: 'timestamp', description: 'When this file is deleted. 30 minutes out by default.' },
      {
        name: 'availableOperations',
        type: 'Operation[]',
        description: 'The subset of the catalog that fits this upload, in the same shape /api/operations returns.',
      },
    ],
    errors: ['413 file_too_large', '415 unsupported_file_type', '422 validation_error', '429 rate_limited'],
    samples: [
      {
        label: 'curl',
        language: 'bash',
        code: `curl -s -X POST ${EXAMPLE_HOST}/api/upload \\
  -F "files=@quarterly-report.pdf"`,
      },
      {
        label: 'Response',
        language: 'json',
        code: `{
  "files": [
    {
      "id": "8f14e45f-ea6c-4f2b-b2a1-2c9a6f1d3e77",
      "originalName": "quarterly-report.pdf",
      "size": 12683264,
      "mimeType": "application/pdf",
      "family": "pdf",
      "pageCount": 18,
      "expiresAt": "2026-07-31T11:34:02Z"
    }
  ],
  "availableOperations": [
    { "key": "compress", "name": "Compress PDF", "implemented": true, "minFiles": 1 },
    { "key": "organize", "name": "Organize Pages", "implemented": true, "minFiles": 1 }
  ]
}`,
      },
    ],
  },
  {
    id: 'get-operations',
    method: 'GET',
    path: '/api/operations',
    group: 'tools',
    summary: 'The tool catalog',
    description:
      'Every operation the service knows about, including ones not built yet. Check `implemented` before offering a tool — an unimplemented key is advertised so clients can show it as coming soon, not so it can be queued.',
    responds: { status: '200', description: 'The full catalog' },
    returns: [
      { name: 'key', type: 'string', description: 'The value you send as `operation`.' },
      { name: 'name', type: 'string', description: 'Human label.' },
      { name: 'description', type: 'string', description: 'One line on what it does.' },
      { name: 'category', type: 'string', description: 'organize, optimize, convert, security or edit.' },
      { name: 'accepts', type: 'string[]', description: 'File families it runs on.' },
      { name: 'multiFile', type: 'boolean', description: 'Whether it takes more than one input.' },
      { name: 'minFiles', type: 'integer', description: 'Fewest inputs it needs.' },
      { name: 'outputExtension', type: 'string', description: 'Extension of the result, e.g. .pdf or .zip.' },
      { name: 'implemented', type: 'boolean', description: 'False means queuing it will fail.' },
      { name: 'optionsSchema', type: 'object', description: 'The shape of `options` for this tool.' },
    ],
    samples: [
      { label: 'curl', language: 'bash', code: `curl -s ${EXAMPLE_HOST}/api/operations` },
      {
        label: 'Response',
        language: 'json',
        code: `[
  {
    "key": "compress",
    "name": "Compress PDF",
    "description": "Shrink a PDF while keeping it readable.",
    "category": "optimize",
    "accepts": ["pdf"],
    "multiFile": false,
    "minFiles": 1,
    "outputExtension": ".pdf",
    "implemented": true,
    "optionsSchema": {
      "level": { "type": "string", "enum": ["low", "medium", "high"] }
    }
  }
]`,
      },
    ],
  },
  {
    id: 'post-jobs-create',
    method: 'POST',
    path: '/api/jobs/create',
    group: 'jobs',
    summary: 'Queue a processing job',
    description:
      'Hands the job to the worker and returns immediately — the response is the job record at `pending`, not the finished result. Field names are accepted in both camelCase and snake_case.',
    rateLimit: '60 requests / minute',
    body: {
      contentType: 'application/json',
      fields: [
        { name: 'operation', type: 'string', description: 'A `key` from /api/operations.' },
        {
          name: 'fileIds',
          type: 'uuid[]',
          note: '1–25',
          description: 'Ids from /api/upload. For multi-file tools the array order is the order used.',
        },
        {
          name: 'options',
          type: 'object',
          note: 'optional, max 32 keys',
          description:
            'Tool-specific settings, matching that tool’s optionsSchema. Organize Pages accepts a `pages` array in output order; each item contains a 1-based `source` page and a `rotation` of 0, 90, 180 or 270.',
        },
      ],
    },
    responds: { status: '201', description: 'Job queued' },
    returns: [
      { name: 'id', type: 'uuid', description: 'Use it to follow, then download.' },
      { name: 'status', type: 'string', description: 'pending, processing, completed, failed or expired.' },
      { name: 'progress', type: 'integer', description: '0–100.' },
      { name: 'stage', type: 'string', note: 'nullable', description: 'What it is doing right now.' },
      { name: 'expiresAt', type: 'timestamp', description: 'When the result is deleted.' },
    ],
    errors: ['404 not_found', '409 conflict', '422 validation_error', '429 rate_limited'],
    samples: [
      {
        label: 'curl',
        language: 'bash',
        code: `curl -s -X POST ${EXAMPLE_HOST}/api/jobs/create \\
  -H "Content-Type: application/json" \\
  -d '{
    "operation": "compress",
    "fileIds": ["8f14e45f-ea6c-4f2b-b2a1-2c9a6f1d3e77"],
    "options": { "level": "medium" }
  }'`,
      },
      {
        label: 'Response',
        language: 'json',
        code: `{
  "id": "b1946ac9-2492-4f6e-8b2c-7c1f0d55e3aa",
  "operation": "compress",
  "status": "pending",
  "progress": 0,
  "stage": "queued",
  "errorMessage": null,
  "inputFilename": "quarterly-report.pdf",
  "outputFilename": null,
  "outputSize": null,
  "createdAt": "2026-07-31T11:04:02Z",
  "completedAt": null,
  "expiresAt": "2026-07-31T11:34:02Z"
}`,
      },
      {
        label: 'Organize pages',
        language: 'bash',
        code: `# Output order: source page 3, then page 1 rotated, then another copy of page 1.
# Omitting a source page deletes it from the result.
curl -s -X POST ${EXAMPLE_HOST}/api/jobs/create \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "organize",
    "fileIds": ["8f14e45f-ea6c-4f2b-b2a1-2c9a6f1d3e77"],
    "options": {
      "pages": [
        { "source": 3, "rotation": 0 },
        { "source": 1, "rotation": 90 },
        { "source": 1, "rotation": 0 }
      ]
    }
  }'`,
      },
      {
        label: 'Office to PDF',
        language: 'bash',
        code: `# Upload the DOCX, XLSX or PPTX first, then use its returned file id.
curl -s -X POST ${EXAMPLE_HOST}/api/jobs/create \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "office_to_pdf",
    "fileIds": ["8f14e45f-ea6c-4f2b-b2a1-2c9a6f1d3e77"],
    "options": {}
  }'`,
      },
    ],
  },
  {
    id: 'get-job-events',
    method: 'GET',
    path: '/api/jobs/{jobId}/events',
    group: 'jobs',
    summary: 'Follow a job over SSE',
    description:
      'A Server-Sent Events stream, and the way to watch a job without polling. Current state is replayed on connect, so a client that attaches late — or after a job that finished in under a second — still sees the terminal event. The server closes the stream itself once the job completes or fails.',
    pathParams: [{ name: 'jobId', type: 'uuid', description: 'From /api/jobs/create.' }],
    responds: { status: '200', description: 'text/event-stream' },
    errors: ['404 not_found', '410 expired'],
    samples: [
      { label: 'curl', language: 'bash', code: `curl -N ${EXAMPLE_HOST}/api/jobs/b1946ac9-2492-4f6e-8b2c-7c1f0d55e3aa/events` },
      {
        label: 'Stream',
        language: 'http',
        code: `event: job_progress
data: {"id":"b1946ac9…","status":"processing","progress":30,"stage":"preparing"}

event: job_progress
data: {"id":"b1946ac9…","status":"processing","progress":60,"stage":"optimizing"}

: keep-alive

event: job_completed
data: {"id":"b1946ac9…","status":"completed","progress":100,"stage":"finishing"}`,
      },
      {
        label: 'Browser',
        language: 'json',
        code: `const stream = new EventSource(\`/api/jobs/\${jobId}/events\`)

for (const name of ['job_created', 'job_progress', 'job_completed', 'job_failed']) {
  stream.addEventListener(name, (event) => {
    const job = JSON.parse(event.data)
    console.log(job.status, job.progress, job.stage)
    if (name !== 'job_progress') stream.close()
  })
}`,
      },
    ],
  },
  {
    id: 'get-job-status',
    method: 'GET',
    path: '/api/jobs/{jobId}/status',
    group: 'jobs',
    summary: 'Poll a job',
    description:
      'The small shape, for clients that cannot hold a stream open. Prefer the SSE endpoint where you can; this exists as the fallback, and it is what the web app itself falls back to.',
    pathParams: [{ name: 'jobId', type: 'uuid', description: 'From /api/jobs/create.' }],
    responds: { status: '200', description: 'Current status' },
    returns: [
      { name: 'id', type: 'uuid', description: 'The job.' },
      { name: 'status', type: 'string', description: 'pending, processing, completed, failed or expired.' },
      { name: 'progress', type: 'integer', description: '0–100.' },
      { name: 'stage', type: 'string', note: 'nullable', description: 'Current step.' },
      { name: 'errorMessage', type: 'string', note: 'nullable', description: 'Set when status is failed.' },
    ],
    errors: ['404 not_found', '410 expired'],
    samples: [
      { label: 'curl', language: 'bash', code: `curl -s ${EXAMPLE_HOST}/api/jobs/b1946ac9-2492-4f6e-8b2c-7c1f0d55e3aa/status` },
      {
        label: 'Response',
        language: 'json',
        code: `{
  "id": "b1946ac9-2492-4f6e-8b2c-7c1f0d55e3aa",
  "status": "processing",
  "progress": 60,
  "stage": "optimizing",
  "errorMessage": null
}`,
      },
    ],
  },
  {
    id: 'get-job',
    method: 'GET',
    path: '/api/jobs/{jobId}',
    group: 'jobs',
    summary: 'Read the full job record',
    description:
      'Everything the status endpoint returns, plus filenames, output size and timestamps. Useful once a job is done and you want to describe the result.',
    pathParams: [{ name: 'jobId', type: 'uuid', description: 'From /api/jobs/create.' }],
    responds: { status: '200', description: 'The job record' },
    returns: [
      { name: 'operation', type: 'string', description: 'The tool that ran.' },
      { name: 'inputFilename', type: 'string', note: 'nullable', description: 'Display name of the input.' },
      { name: 'outputFilename', type: 'string', note: 'nullable', description: 'Name the download is served under.' },
      { name: 'outputSize', type: 'integer', note: 'nullable', description: 'Bytes of the result.' },
      { name: 'createdAt', type: 'timestamp', description: 'When it was queued.' },
      { name: 'completedAt', type: 'timestamp', note: 'nullable', description: 'When it finished.' },
      { name: 'expiresAt', type: 'timestamp', description: 'When the result is deleted.' },
    ],
    errors: ['404 not_found', '410 expired'],
    samples: [
      { label: 'curl', language: 'bash', code: `curl -s ${EXAMPLE_HOST}/api/jobs/b1946ac9-2492-4f6e-8b2c-7c1f0d55e3aa` },
    ],
  },
  {
    id: 'get-download',
    method: 'GET',
    path: '/api/download/{jobId}',
    group: 'result',
    summary: 'Download the result',
    description:
      'Streams the finished file. There is no listing and no index — a job id is the only way to reach a result, and the link stops working the moment the file is swept.',
    pathParams: [{ name: 'jobId', type: 'uuid', description: 'A job whose status is completed.' }],
    responds: { status: '200', description: 'The file, as a binary body' },
    returns: [
      {
        name: 'Content-Disposition',
        type: 'header',
        description: 'attachment, with both the ASCII and RFC 5987 forms of the filename.',
      },
      { name: 'Content-Type', type: 'header', description: 'application/pdf, application/zip, image/png or image/jpeg.' },
      { name: 'Cache-Control', type: 'header', description: 'Always no-store.' },
    ],
    errors: ['404 not_found', '409 conflict — still processing, or the job failed', '410 expired'],
    samples: [
      { label: 'curl', language: 'bash', code: `# -OJ keeps the filename the server sends
curl -OJ ${EXAMPLE_HOST}/api/download/b1946ac9-2492-4f6e-8b2c-7c1f0d55e3aa` },
    ],
  },
  {
    id: 'get-health',
    method: 'GET',
    path: '/api/health',
    group: 'system',
    summary: 'Liveness and dependencies',
    description:
      'Returns 200 while the database and Redis both answer, and 503 with status "degraded" when either does not. Safe to point a load balancer at.',
    responds: { status: '200 / 503', description: 'ok, or degraded' },
    returns: [
      { name: 'status', type: 'string', description: 'ok or degraded.' },
      { name: 'version', type: 'string', description: 'API version.' },
      { name: 'database', type: 'string', description: 'up or down.' },
      { name: 'redis', type: 'string', description: 'up or down.' },
    ],
    samples: [
      { label: 'curl', language: 'bash', code: `curl -s ${EXAMPLE_HOST}/api/health` },
      {
        label: 'Response',
        language: 'json',
        code: `{ "status": "ok", "version": "0.1.0", "database": "up", "redis": "up" }`,
      },
    ],
  },
  {
    id: 'get-config',
    method: 'GET',
    path: '/api/config',
    group: 'system',
    summary: 'Client-visible limits',
    description:
      'The limits the server is actually running with. Read these at startup instead of hardcoding them — they are deployment settings, not constants.',
    responds: { status: '200', description: 'Current limits' },
    returns: [
      { name: 'maxUploadBytes', type: 'integer', description: 'Largest accepted file.' },
      { name: 'maxFilesPerJob', type: 'integer', description: 'Most files in one upload or job.' },
      { name: 'fileTtlMinutes', type: 'integer', description: 'How long anything survives.' },
    ],
    samples: [
      { label: 'curl', language: 'bash', code: `curl -s ${EXAMPLE_HOST}/api/config` },
      {
        label: 'Response',
        language: 'json',
        code: `{ "maxUploadBytes": 104857600, "maxFilesPerJob": 25, "fileTtlMinutes": 30 }`,
      },
    ],
  },
]

/** The end-to-end flow, which is the thing a reference page can show and a schema browser cannot. */
export const QUICKSTART = {
  language: 'bash' as const,
  code: `# 1 — upload. The response lists the tools that fit what you sent.
curl -s -X POST ${EXAMPLE_HOST}/api/upload \\
  -F "files=@quarterly-report.pdf" | jq '.files[0].id, .availableOperations[].key'

# 2 — queue a job against the file id you got back.
curl -s -X POST ${EXAMPLE_HOST}/api/jobs/create \\
  -H "Content-Type: application/json" \\
  -d '{"operation":"compress","fileIds":["<file-id>"],"options":{"level":"medium"}}' | jq '.id'

# 3 — follow it. The server closes the stream when the job ends.
curl -N ${EXAMPLE_HOST}/api/jobs/<job-id>/events

# 4 — collect the result, before the 30 minutes are up.
curl -OJ ${EXAMPLE_HOST}/api/download/<job-id>`,
}

export const JOB_STATUSES = [
  { name: 'pending', terminal: false, description: 'Queued, not picked up yet.' },
  { name: 'processing', terminal: false, description: 'A worker has it.' },
  { name: 'completed', terminal: true, description: 'The result is ready to download.' },
  { name: 'failed', terminal: true, description: 'Read `errorMessage` for the reason.' },
  { name: 'expired', terminal: true, description: 'The retention window closed and the file is gone.' },
]

/** Stage strings the worker emits, in the order a job passes through them. */
export const JOB_STAGES = [
  { name: 'queued', at: '0%', description: 'Accepted, waiting for a worker.' },
  { name: 'preparing', at: '10–30%', description: 'Inputs opened and validated.' },
  { name: 'merging / splitting / optimizing', at: '30–80%', description: 'The operation itself. Which one depends on the tool.' },
  { name: 'writing', at: '80%', description: 'The result is being written out.' },
  { name: 'finishing', at: '90–100%', description: 'Result recorded, inputs deleted.' },
]

export const SSE_EVENTS = [
  { name: 'job_created', description: 'Sent once, when the job record exists.' },
  { name: 'job_progress', description: 'Sent on every progress change. Also the replayed opening frame.' },
  { name: 'job_completed', description: 'Terminal. The server closes the stream after this.' },
  { name: 'job_failed', description: 'Terminal. `errorMessage` carries the safe reason.' },
]

export const ERROR_CODES = [
  { status: 413, code: 'file_too_large', description: 'A file was over `maxUploadBytes`.' },
  { status: 415, code: 'unsupported_file_type', description: 'The extension is not allowed, or the bytes do not match it.' },
  { status: 422, code: 'validation_error', description: 'Something in the request was not usable.' },
  { status: 422, code: 'invalid_request', description: 'The body did not match the schema at all.' },
  { status: 404, code: 'not_found', description: 'No such file, job or result.' },
  { status: 409, code: 'conflict', description: 'The job is not in a state that allows this — usually still processing.' },
  { status: 410, code: 'expired', description: 'It existed, and has since been deleted.' },
  { status: 429, code: 'rate_limited', description: 'Slow down and retry.' },
  { status: 500, code: 'internal_error', description: 'Something broke. The cause is logged, never returned.' },
]

export const LIMITS = [
  { label: 'Largest file', value: '100 MB', note: 'per file, not per request' },
  { label: 'Files per request', value: '25', note: 'upload and job alike' },
  { label: 'Retention', value: '30 minutes', note: 'inputs go as soon as the job ends' },
  { label: 'Uploads', value: '30 / min', note: 'per client address' },
  { label: 'Job creation', value: '60 / min', note: 'per client address' },
]

export const ACCEPTED_TYPES = [
  { family: 'pdf', extensions: '.pdf' },
  { family: 'image', extensions: '.jpg, .jpeg, .png, .webp' },
  { family: 'office', extensions: '.docx, .xlsx, .pptx' },
]
