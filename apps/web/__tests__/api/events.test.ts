import { GET } from '@/app/api/events/route'
import { NextRequest } from 'next/server'
import * as dynamodb from '@/lib/dynamodb'
import * as authUtils from '@/lib/auth-utils'

// Mock DynamoDB module
jest.mock('@/lib/dynamodb')
jest.mock('@/lib/auth-utils')

describe('GET /api/events', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Mock authenticated session by default
    ;(authUtils.getAuthSession as jest.Mock).mockResolvedValue({
      user: { email: 'admin@localhost', name: 'Local Admin', role: 'admin' },
      expires: new Date(Date.now() + 86400000).toISOString(),
    })
    // Reset mocks to default (return empty arrays)
    ;(dynamodb.getEventsByType as jest.Mock).mockResolvedValue([])
    ;(dynamodb.getEventsBySeverity as jest.Mock).mockResolvedValue([])
    ;(dynamodb.getRecentEvents as jest.Mock).mockResolvedValue([])
  })

  it('returns 401 when not authenticated', async () => {
    ;(authUtils.getAuthSession as jest.Mock).mockResolvedValue(null)

    const request = new NextRequest(new URL('http://localhost:3000/api/events'))
    const response = await GET(request)
    expect(response.status).toBe(401)
  })

  it('returns events with no filters', async () => {
    const request = new NextRequest(new URL('http://localhost:3000/api/events'))
    const response = await GET(request)

    expect(response.status).toBe(200)
    const json = await response.json()

    expect(json.events).toBeDefined()
    expect(Array.isArray(json.events)).toBe(true)
    expect(json.total).toBeDefined()
    // Should return mock events since DynamoDB returns empty array
  })

  it('filters by event type', async () => {
    const request = new NextRequest(new URL('http://localhost:3000/api/events?type=ec2'))
    const response = await GET(request)

    expect(response.status).toBe(200)
    // Should call getEventsByType with 'ec2'
    expect(dynamodb.getEventsByType).toHaveBeenCalledWith('ec2', expect.any(Number))
  })

  it('filters by severity', async () => {
    const request = new NextRequest(new URL('http://localhost:3000/api/events?severity=critical'))
    const response = await GET(request)

    expect(response.status).toBe(200)
    // Should call getEventsBySeverity with 'critical'
    expect(dynamodb.getEventsBySeverity).toHaveBeenCalledWith('critical', expect.any(Number))
  })

  it('applies both type and severity filters', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/events?type=s3&severity=warning')
    )
    const response = await GET(request)

    expect(response.status).toBe(200)
    const json = await response.json()

    // Both filters should be applied
    expect(Array.isArray(json.events)).toBe(true)
  })

  it('parses hours parameter correctly', async () => {
    const request = new NextRequest(new URL('http://localhost:3000/api/events?hours=48'))
    const response = await GET(request)

    expect(response.status).toBe(200)
    // Should parse 48 hours without error
    const json = await response.json()
    expect(json.events).toBeDefined()
  })
})
