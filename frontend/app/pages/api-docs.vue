<script setup lang="ts">
import {
  ACCEPTED_TYPES,
  ENDPOINTS,
  ERROR_CODES,
  EXAMPLE_HOST,
  GROUPS,
  JOB_STAGES,
  JOB_STATUSES,
  LIMITS,
  QUICKSTART,
  SSE_EVENTS,
} from '~/utils/apiReference'

useSeo({
  title: 'PDFFlow API — reference for the no-signup PDF API',
  description:
    'Upload, queue a job, follow it over SSE and download the result. No keys, no accounts, nothing stored.',
})

const overviewSections = [
  { id: 'overview', label: 'Overview' },
  { id: 'quickstart', label: 'Quickstart' },
]
const tailSections = [
  { id: 'lifecycle', label: 'Job lifecycle' },
  { id: 'errors', label: 'Errors' },
  { id: 'limits', label: 'Limits' },
]

function endpointsIn(group: string) {
  return ENDPOINTS.filter((endpoint) => endpoint.group === group)
}

const spyIds = computed(() => [
  ...overviewSections.map((section) => section.id),
  ...ENDPOINTS.map((endpoint) => endpoint.id),
  ...tailSections.map((section) => section.id),
])

const { active } = useScrollSpy(spyIds)

const errorEnvelope = [
  {
    label: 'Shape',
    language: 'json' as const,
    code: `{
  "error": {
    "code": "expired",
    "message": "This result has expired and was deleted.",
    "requestId": "e69ea9ba8619"
  }
}`,
  },
]

const baseUrlSample = [
  {
    label: 'Base URL',
    language: 'bash' as const,
    code: `# Same origin as the app in production — no separate API host.
${EXAMPLE_HOST}/api

# No key, no token, no Authorization header. There is no account to attach
# a request to, so there is nothing to authenticate.
curl -s ${EXAMPLE_HOST}/api/health`,
  },
]
</script>

<template>
  <div class="mx-auto max-w-6xl px-5 py-12 sm:px-6">
    <!-- ==================== Masthead ==================== -->
    <header class="max-w-2xl">
      <p class="eyebrow">API reference · v0.1.0</p>
      <h1
        class="font-display mt-5 text-4xl font-bold leading-[1.02] tracking-[-0.025em] text-ink sm:text-[3.25rem]"
      >
        Four calls, and the file<br>
        <span class="mark mark-draw" style="--enter-delay: 0.35s">deletes itself.</span>
      </h1>
      <p class="mt-5 text-pretty text-lg leading-relaxed text-ink-muted">
        Upload, queue a job, follow it, download the result. There are no keys to
        request and no accounts to create — the same guarantees the web app gets
        are the ones you get.
      </p>
    </header>

    <div class="mt-12 gap-10 lg:grid lg:grid-cols-[190px_1fr] lg:gap-12">
      <!-- ==================== Sidebar ==================== -->
      <!-- Sticky on desktop only. On a phone it would eat a third of the screen
           to duplicate a list you can reach by scrolling. -->
      <aside class="hidden lg:block">
        <nav class="sticky top-24 space-y-6" aria-label="API reference">
          <ul class="space-y-1">
            <li v-for="section in overviewSections" :key="section.id">
              <a
                :href="`#${section.id}`"
                class="block border-l py-1 pl-3 text-sm transition-colors duration-150"
                :class="
                  active === section.id
                    ? 'border-accent-400 text-accent-ink'
                    : 'border-hairline text-ink-muted hover:border-hairline-strong hover:text-ink'
                "
              >{{ section.label }}</a>
            </li>
          </ul>

          <div v-for="group in GROUPS" :key="group.id">
            <p class="font-data mb-1.5 text-[10px] uppercase tracking-[0.2em] text-ink-faint">
              {{ group.label }}
            </p>
            <ul class="space-y-1">
              <li v-for="endpoint in endpointsIn(group.id)" :key="endpoint.id">
                <a
                  :href="`#${endpoint.id}`"
                  class="block border-l py-1 pl-3 text-sm transition-colors duration-150"
                  :class="
                    active === endpoint.id
                      ? 'border-accent-400 text-accent-ink'
                      : 'border-hairline text-ink-muted hover:border-hairline-strong hover:text-ink'
                  "
                >{{ endpoint.summary }}</a>
              </li>
            </ul>
          </div>

          <ul class="space-y-1">
            <li v-for="section in tailSections" :key="section.id">
              <a
                :href="`#${section.id}`"
                class="block border-l py-1 pl-3 text-sm transition-colors duration-150"
                :class="
                  active === section.id
                    ? 'border-accent-400 text-accent-ink'
                    : 'border-hairline text-ink-muted hover:border-hairline-strong hover:text-ink'
                "
              >{{ section.label }}</a>
            </li>
          </ul>
        </nav>
      </aside>

      <div class="min-w-0 space-y-16">
        <!-- ==================== Overview ==================== -->
        <section id="overview" class="scroll-mt-24">
          <h2 class="font-display text-2xl font-bold tracking-[-0.02em] text-ink">
            Overview
          </h2>
          <p class="mt-3 max-w-2xl text-pretty leading-relaxed text-ink-muted">
            Every response is JSON except a download, which is the file itself.
            Field names are camelCase going out; request bodies accept either
            camelCase or snake_case. Timestamps are ISO 8601 in UTC.
          </p>

          <div class="mt-5">
            <CodeBlock :samples="baseUrlSample" />
          </div>

          <dl class="mt-6 grid gap-5 sm:grid-cols-3">
            <div v-for="item in [
              { term: 'No authentication', detail: 'Nothing to send. Rate limits are per client address instead of per key.' },
              { term: 'Nothing retained', detail: 'Inputs are deleted when a job ends, results within 30 minutes. There is no listing endpoint.' },
              { term: 'CORS', detail: 'Locked to the configured origins. Credentials are never accepted — there are none.' },
            ]" :key="item.term" class="border-t border-hairline pt-3">
              <dt class="font-medium text-ink">{{ item.term }}</dt>
              <dd class="mt-1 text-sm leading-relaxed text-ink-muted">{{ item.detail }}</dd>
            </div>
          </dl>
        </section>

        <!-- ==================== Quickstart ==================== -->
        <section id="quickstart" class="scroll-mt-24">
          <h2 class="font-display text-2xl font-bold tracking-[-0.02em] text-ink">
            Quickstart
          </h2>
          <p class="mt-3 max-w-2xl text-pretty leading-relaxed text-ink-muted">
            The whole flow, start to finish. Swap in your own host and file, then
            paste the four commands in order.
          </p>
          <div class="mt-5">
            <CodeBlock :samples="[{ label: 'End to end', language: QUICKSTART.language, code: QUICKSTART.code }]" />
          </div>
        </section>

        <!-- ==================== Endpoints ==================== -->
        <section v-for="group in GROUPS" :key="group.id" class="space-y-4">
          <div class="flex items-baseline gap-4">
            <h2 class="font-data text-xs uppercase tracking-[0.2em] text-ink">
              {{ group.label }}
            </h2>
            <span class="hidden text-sm text-ink-faint sm:inline">{{ group.blurb }}</span>
            <span class="h-px flex-1 bg-hairline" aria-hidden="true" />
          </div>

          <ApiEndpoint
            v-for="endpoint in endpointsIn(group.id)"
            :key="endpoint.id"
            :endpoint="endpoint"
          />
        </section>

        <!-- ==================== Lifecycle ==================== -->
        <section id="lifecycle" class="scroll-mt-24">
          <h2 class="font-display text-2xl font-bold tracking-[-0.02em] text-ink">
            Job lifecycle
          </h2>
          <p class="mt-3 max-w-2xl text-pretty leading-relaxed text-ink-muted">
            A job moves through one of five statuses. Three of them are terminal:
            once you see one, stop asking.
          </p>

          <div class="panel mt-5 p-5 sm:p-6">
            <dl class="space-y-3">
              <div
                v-for="status in JOB_STATUSES"
                :key="status.name"
                class="grid gap-x-4 gap-y-1 sm:grid-cols-[minmax(0,11rem)_1fr]"
              >
                <dt class="flex items-center gap-2">
                  <span
                    class="size-1.5 rounded-full"
                    :class="status.terminal ? 'bg-good' : 'bg-accent-400'"
                    aria-hidden="true"
                  />
                  <code class="font-data text-[13px] text-ink">{{ status.name }}</code>
                  <span v-if="status.terminal" class="font-data text-[10px] uppercase tracking-[0.14em] text-ink-faint">
                    terminal
                  </span>
                </dt>
                <dd class="text-sm leading-relaxed text-ink-muted">
                  <DocProse :text="status.description" />
                </dd>
              </div>
            </dl>

            <!-- Stages are a genuine ordered walk, so they get the rail. -->
            <div class="mt-8">
              <div class="mb-3 flex items-baseline gap-3">
                <h3 class="font-data text-[11px] uppercase tracking-[0.18em] text-ink-faint">
                  Stages, in order
                </h3>
                <span class="h-px flex-1 bg-hairline" aria-hidden="true" />
              </div>
              <div class="fuse mb-5 hidden sm:block" style="--burn: 100%" aria-hidden="true" />
              <ol class="grid gap-5 sm:grid-cols-3 lg:grid-cols-5">
                <li
                  v-for="stage in JOB_STAGES"
                  :key="stage.name"
                  class="relative border-l border-hairline pl-3 sm:border-l-0 sm:pl-0"
                >
                  <span
                    class="absolute -top-5 left-0 hidden h-3 w-px bg-hairline-strong sm:block"
                    aria-hidden="true"
                  />
                  <p class="font-data text-xs tabular-nums text-accent-ink">{{ stage.at }}</p>
                  <code class="font-data mt-1.5 block text-[13px] text-ink">{{ stage.name }}</code>
                  <p class="mt-1 text-sm leading-relaxed text-ink-muted">{{ stage.description }}</p>
                </li>
              </ol>
            </div>

            <div class="mt-8">
              <div class="mb-3 flex items-baseline gap-3">
                <h3 class="font-data text-[11px] uppercase tracking-[0.18em] text-ink-faint">
                  SSE event names
                </h3>
                <span class="h-px flex-1 bg-hairline" aria-hidden="true" />
              </div>
              <dl class="space-y-2.5">
                <div
                  v-for="event in SSE_EVENTS"
                  :key="event.name"
                  class="grid gap-x-4 gap-y-1 sm:grid-cols-[minmax(0,11rem)_1fr]"
                >
                  <dt><code class="font-data text-[13px] text-ink">{{ event.name }}</code></dt>
                  <dd class="text-sm leading-relaxed text-ink-muted">
                    <DocProse :text="event.description" />
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </section>

        <!-- ==================== Errors ==================== -->
        <section id="errors" class="scroll-mt-24">
          <h2 class="font-display text-2xl font-bold tracking-[-0.02em] text-ink">
            Errors
          </h2>
          <p class="mt-3 max-w-2xl text-pretty leading-relaxed text-ink-muted">
            Every failure uses the same envelope. Match on <code class="font-data text-[13px] text-ink">code</code>,
            not on the message — messages are written for people and will change.
            <code class="font-data text-[13px] text-ink">requestId</code> also comes back
            as the <code class="font-data text-[13px] text-ink">X-Request-Id</code> header, and quoting
            it is how a failure gets traced in the logs.
          </p>

          <div class="mt-5">
            <CodeBlock :samples="errorEnvelope" />
          </div>

          <div class="panel mt-5 p-5 sm:p-6">
            <dl class="space-y-2.5">
              <div
                v-for="error in ERROR_CODES"
                :key="error.code"
                class="grid gap-x-4 gap-y-1 sm:grid-cols-[minmax(0,15rem)_1fr]"
              >
                <dt class="flex items-baseline gap-2.5">
                  <span class="font-data text-xs tabular-nums text-accent-ink">{{ error.status }}</span>
                  <code class="font-data text-[13px] text-ink">{{ error.code }}</code>
                </dt>
                <dd class="text-sm leading-relaxed text-ink-muted">
                  <DocProse :text="error.description" />
                </dd>
              </div>
            </dl>
          </div>
        </section>

        <!-- ==================== Limits ==================== -->
        <section id="limits" class="scroll-mt-24">
          <h2 class="font-display text-2xl font-bold tracking-[-0.02em] text-ink">
            Limits
          </h2>
          <p class="mt-3 max-w-2xl text-pretty leading-relaxed text-ink-muted">
            These are the defaults. They are deployment settings, so read
            <code class="font-data text-[13px] text-ink">/api/config</code> at startup rather
            than hardcoding them.
          </p>

          <dl class="mt-5 grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
            <div v-for="limit in LIMITS" :key="limit.label" class="panel p-4">
              <dt class="font-data text-[10px] uppercase tracking-[0.16em] text-ink-faint">
                {{ limit.label }}
              </dt>
              <dd class="font-data mt-1.5 text-lg tabular-nums text-ink">{{ limit.value }}</dd>
              <dd class="mt-0.5 text-xs leading-snug text-ink-faint">{{ limit.note }}</dd>
            </div>
          </dl>

          <div class="panel mt-4 p-5 sm:p-6">
            <div class="mb-3 flex items-baseline gap-3">
              <h3 class="font-data text-[11px] uppercase tracking-[0.18em] text-ink-faint">
                Accepted file types
              </h3>
              <span class="h-px flex-1 bg-hairline" aria-hidden="true" />
            </div>
            <p class="mb-4 max-w-2xl text-sm leading-relaxed text-ink-muted">
              The extension has to be on this list <em>and</em> the file's leading
              bytes have to match it. A <code class="font-data text-[13px] text-ink">.pdf</code>
              that is really a ZIP is rejected with
              <code class="font-data text-[13px] text-ink">unsupported_file_type</code>.
            </p>
            <dl class="space-y-2.5">
              <div
                v-for="type in ACCEPTED_TYPES"
                :key="type.family"
                class="grid gap-x-4 gap-y-1 sm:grid-cols-[minmax(0,11rem)_1fr]"
              >
                <dt><code class="font-data text-[13px] text-ink">{{ type.family }}</code></dt>
                <dd class="font-data text-sm text-ink-muted">{{ type.extensions }}</dd>
              </div>
            </dl>
          </div>
        </section>

        <!-- ==================== Schema browsers ==================== -->
        <section class="panel p-5 sm:p-6">
          <h2 class="font-display text-xl font-bold tracking-tight text-ink">
            Prefer to poke at it live?
          </h2>
          <p class="mt-2 max-w-2xl text-pretty leading-relaxed text-ink-muted">
            The generated schema and an interactive console are both still served
            straight off the API.
          </p>
          <div class="mt-4 flex flex-wrap gap-2">
            <UButton to="/docs" external target="_blank" variant="outline" color="neutral" icon="i-lucide-terminal">
              Swagger UI
            </UButton>
            <UButton to="/redoc" external target="_blank" variant="outline" color="neutral" icon="i-lucide-book-open">
              ReDoc
            </UButton>
            <UButton to="/openapi.json" external target="_blank" variant="outline" color="neutral" icon="i-lucide-braces">
              openapi.json
            </UButton>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
