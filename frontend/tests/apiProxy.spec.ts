import { describe, expect, it } from 'vitest'

import { apiProxyTarget } from '../server/utils/apiProxy'

describe('apiProxyTarget', () => {
  it('forwards an API path and query string to the private backend', () => {
    expect(
      apiProxyTarget(
        'http://backend.railway.internal:8000/api',
        '/api/jobs/abc/status?detail=true',
      ),
    ).toBe('http://backend.railway.internal:8000/api/jobs/abc/status?detail=true')
  })

  it('handles a trailing slash on the configured backend URL', () => {
    expect(apiProxyTarget('http://api:8000/api/', '/api/health')).toBe(
      'http://api:8000/api/health',
    )
  })

  it('refuses to proxy non-API paths', () => {
    expect(() => apiProxyTarget('http://api:8000/api', '/admin')).toThrow(
      'Only API paths can be proxied',
    )
  })
})
