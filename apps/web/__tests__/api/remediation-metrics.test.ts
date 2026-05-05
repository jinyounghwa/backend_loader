import { GET } from '@/app/api/remediation-metrics/route'
import { NextRequest } from 'next/server'
import * as authUtils from '@/lib/auth-utils'

// Mock the auth utilities
jest.mock('@/lib/auth-utils')

describe('GET /api/remediation-metrics', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Mock authenticated session by default
    ;(authUtils.getAuthSession as jest.Mock).mockResolvedValue({
      user: { email: 'admin@localhost', name: 'Local Admin', role: 'admin' },
      expires: new Date(Date.now() + 86400000).toISOString(),
    })
  })

  it('returns 401 when not authenticated', async () => {
    // Mock unauthenticated session
    ;(authUtils.getAuthSession as jest.Mock).mockResolvedValue(null)

    const request = new NextRequest(new URL('http://localhost:3000/api/remediation-metrics'))
    const response = await GET(request)

    expect(response.status).toBe(401)
    const json = await response.json()
    expect(json.error).toBe('Unauthorized')
  })

  it('returns metrics with no query parameters', async () => {
    const request = new NextRequest(new URL('http://localhost:3000/api/remediation-metrics'))
    const response = await GET(request)

    expect(response.status).toBe(200)
    const json = await response.json()

    expect(json.success).toBe(true)
    expect(Array.isArray(json.metrics)).toBe(true)
    expect(json.metrics.length).toBe(3) // 3 mock rules
    expect(json.summary).toBeDefined()
    expect(json.summary.total_rules).toBe(3)
    expect(json.summary.avg_effectiveness_score).toBeDefined()
    expect(json.timestamp).toBeDefined()
  })

  it('filters metrics by rule_id', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/remediation-metrics?rule_id=rule-001')
    )
    const response = await GET(request)

    expect(response.status).toBe(200)
    const json = await response.json()

    expect(json.metrics.length).toBe(1)
    expect(json.metrics[0].rule_id).toBe('rule-001')
    expect(json.summary.total_rules).toBe(1)
  })

  it('returns empty metrics when rule_id does not exist', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/remediation-metrics?rule_id=nonexistent')
    )
    const response = await GET(request)

    expect(response.status).toBe(200)
    const json = await response.json()

    expect(json.metrics.length).toBe(0)
    // When empty array, the route returns 0 instead of NaN
    expect(json.summary.avg_effectiveness_score).toBe(0)
  })

  it('accepts days parameter without error', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/remediation-metrics?days=7')
    )
    const response = await GET(request)

    expect(response.status).toBe(200)
    const json = await response.json()

    // Should parse days parameter without error
    expect(json.metrics.length).toBe(3)
  })
})
