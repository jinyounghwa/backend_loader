import { GET } from '@/app/api/status/route'
import { NextRequest } from 'next/server'
import * as dynamodb from '@/lib/dynamodb'
import * as authUtils from '@/lib/auth-utils'

jest.mock('@/lib/dynamodb')
jest.mock('@/lib/auth-utils')

describe('GET /api/status', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Mock authenticated session by default
    ;(authUtils.getAuthSession as jest.Mock).mockResolvedValue({
      user: { email: 'admin@localhost', name: 'Local Admin', role: 'admin' },
      expires: new Date(Date.now() + 86400000).toISOString(),
    })
    ;(dynamodb.getLatestCheckResultOptimized as jest.Mock).mockResolvedValue(null)
    ;(dynamodb.getRecentEvents as jest.Mock).mockResolvedValue([])
  })

  it('returns 401 when not authenticated', async () => {
    ;(authUtils.getAuthSession as jest.Mock).mockResolvedValue(null)

    const request = new NextRequest(new URL('http://localhost:3000/api/status'))
    const response = await GET(request)
    expect(response.status).toBe(401)
  })

  it('returns single-region status by default', async () => {
    const request = new NextRequest(new URL('http://localhost:3000/api/status'))
    const response = await GET(request)

    expect(response.status).toBe(200)
    const json = await response.json()

    // Should return DashboardSummary shape (not MultiRegionSummary)
    expect(json.cost).toBeDefined()
    expect(json.ec2).toBeDefined()
    expect(json.s3).toBeDefined()
    expect(json.recent_events).toBeDefined()
    expect(json.system_health).toBeDefined()
    // Should NOT have 'regions' array (that's for multi-region)
    expect(json.regions).toBeUndefined()
  })

  it('returns multi-region status when regions parameter is provided', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/status?regions=ap-northeast-1,us-east-1')
    )
    const response = await GET(request)

    expect(response.status).toBe(200)
    const json = await response.json()

    // Should return MultiRegionSummary shape
    expect(json.regions).toBeDefined()
    expect(Array.isArray(json.regions)).toBe(true)
    expect(json.last_check).toBeDefined()
    // Each region should have its own summary
  })

  it('returns single-region via query param correctly', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/status?regions=ap-northeast-1')
    )
    const response = await GET(request)

    expect(response.status).toBe(200)
    const json = await response.json()

    // When single region via param, should return DashboardSummary not array
    expect(json.cost).toBeDefined()
    expect(json.regions).toBeUndefined()
  })

  it('returns fallback summary when DynamoDB has no data', async () => {
    // When DynamoDB returns null, buildFallbackSummary is used which has is_stale: false
    ;(dynamodb.getLatestCheckResultOptimized as jest.Mock).mockResolvedValue(null)

    const request = new NextRequest(new URL('http://localhost:3000/api/status'))
    const response = await GET(request)

    expect(response.status).toBe(200)
    const json = await response.json()

    // Fallback summary has is_stale: false (hard-coded)
    expect(json.is_stale).toBe(false)
    expect(json.cost).toBeDefined()
    expect(json.ec2).toBeDefined()
    expect(json.s3).toBeDefined()
  })
})
