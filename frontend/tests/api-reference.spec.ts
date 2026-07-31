import { describe, expect, it } from 'vitest'
import {
  ENDPOINTS,
  ERROR_CODES,
  GROUPS,
  JOB_STATUSES,
  type DocEndpoint,
} from '~/utils/apiReference'
import { highlight } from '~/utils/highlight'
import { topmostVisible } from '~/composables/useScrollSpy'

/** Where the dev stack's nginx sits. Matches .claude/launch.json. */
const STACK = process.env.PDFFLOW_STACK_ORIGIN || 'http://localhost:8080'

describe('api reference data', () => {
  it('gives every endpoint a unique anchor id', () => {
    const ids = ENDPOINTS.map((e) => e.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('files every endpoint under a declared group', () => {
    const groups = new Set(GROUPS.map((g) => g.id))
    for (const endpoint of ENDPOINTS) {
      expect(groups, `${endpoint.path} has group "${endpoint.group}"`).toContain(endpoint.group)
    }
  })

  it('leaves no group without endpoints', () => {
    for (const group of GROUPS) {
      expect(
        ENDPOINTS.filter((e) => e.group === group.id).length,
        `group "${group.id}" would render an empty heading`,
      ).toBeGreaterThan(0)
    }
  })

  it('documents at least one runnable sample per endpoint', () => {
    for (const endpoint of ENDPOINTS) {
      expect(endpoint.samples.length, endpoint.path).toBeGreaterThan(0)
      expect(endpoint.samples.some((s) => s.language === 'bash'), endpoint.path).toBe(true)
    }
  })

  it('only cites error codes the API can actually return', () => {
    const known = new Set(ERROR_CODES.map((e) => e.code))
    for (const endpoint of ENDPOINTS) {
      for (const error of endpoint.errors ?? []) {
        // Entries read "429 rate_limited" or "409 conflict — still processing".
        const code = error.split(/\s+/)[1]!
        expect(known, `${endpoint.path} cites "${code}"`).toContain(code)
      }
    }
  })

  it('never leaves an unmatched backtick in prose', () => {
    // DocProse splits on pairs. An odd count means a stray ` renders literally,
    // which is exactly the bug this guards against.
    const prose = ENDPOINTS.flatMap((endpoint) => [
      endpoint.description,
      ...(endpoint.returns ?? []).map((f) => f.description),
      ...(endpoint.pathParams ?? []).map((f) => f.description),
      ...(endpoint.body?.fields ?? []).map((f) => f.description),
    ])
    for (const text of prose) {
      const ticks = (text.match(/`/g) ?? []).length
      expect(ticks % 2, `unbalanced backticks in "${text.slice(0, 50)}…"`).toBe(0)
    }
  })

  it('marks exactly the three terminal job statuses', () => {
    expect(JOB_STATUSES.filter((s) => s.terminal).map((s) => s.name)).toEqual([
      'completed',
      'failed',
      'expired',
    ])
  })
})

describe('topmostVisible', () => {
  it('has nothing to highlight when nothing is visible', () => {
    expect(topmostVisible(new Map())).toBeNull()
  })

  it('picks the section nearest the top of the reading area', () => {
    const visible = new Map([
      ['errors', 480],
      ['limits', 90],
      ['lifecycle', 210],
    ])
    expect(topmostVisible(visible)).toBe('limits')
  })

  it('prefers a section scrolled above the fold over one below it', () => {
    // Scrolling up: the heading coming back into view has a negative top, and
    // it is the one being read.
    expect(topmostVisible(new Map([['a', -40], ['b', 300]]))).toBe('a')
  })

  it('is insensitive to the order entries arrived in', () => {
    const forwards = new Map([['a', 10], ['b', 400]])
    const backwards = new Map([['b', 400], ['a', 10]])
    expect(topmostVisible(forwards)).toBe(topmostVisible(backwards))
  })
})

describe('highlight', () => {
  it('escapes markup before adding any of its own', () => {
    const out = highlight('<script>alert(1)</script>', 'bash')
    expect(out).not.toContain('<script>')
    expect(out).toContain('&lt;script&gt;')
  })

  it('marks json keys and strings apart', () => {
    const out = highlight('{ "level": "medium" }', 'json')
    expect(out).toContain('tok-key')
    expect(out).toContain('tok-string')
  })

  it('marks shell comments and flags', () => {
    const out = highlight('# upload it\ncurl -s --fail url', 'bash')
    expect(out).toContain('tok-comment')
    expect(out).toContain('tok-flag')
  })

  it('marks SSE field names', () => {
    expect(highlight('event: job_progress\ndata: {"progress":30}', 'http')).toContain('tok-keyword')
  })
})

/**
 * The reference is hand-written, so it can drift from the routes. This compares
 * it against the running API when one is reachable and skips otherwise, so it
 * catches drift during development without failing an offline checkout or CI.
 */
describe('api reference matches the live API', () => {
  async function liveOperations(): Promise<Set<string> | null> {
    try {
      const response = await fetch(`${STACK}/openapi.json`, {
        signal: AbortSignal.timeout(2000),
      })
      if (!response.ok) return null
      const schema = (await response.json()) as {
        paths: Record<string, Record<string, unknown>>
      }
      const live = new Set<string>()
      for (const [path, methods] of Object.entries(schema.paths)) {
        for (const method of Object.keys(methods)) {
          if (method === 'parameters') continue
          live.add(`${method.toUpperCase()} ${path}`)
        }
      }
      return live
    } catch {
      return null
    }
  }

  // FastAPI writes path params as {job_id}; the docs show them camelCased.
  const documented = (endpoint: DocEndpoint) =>
    `${endpoint.method} ${endpoint.path.replace(/\{jobId\}/g, '{job_id}')}`

  it('covers every path the API exposes, and invents none', async () => {
    const live = await liveOperations()
    if (!live) {
      console.info(`skipped: no API at ${STACK} — start the stack to check for drift`)
      return
    }

    const ours = new Set(ENDPOINTS.map(documented))
    const missing = [...live].filter((op) => !ours.has(op))
    const stale = [...ours].filter((op) => !live.has(op))

    expect(missing, 'undocumented endpoints').toEqual([])
    expect(stale, 'documented endpoints the API no longer has').toEqual([])
  })
})
