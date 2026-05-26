import { POST } from '@/app/api/guardian/ml/patterns/route'
import { NextRequest } from 'next/server'

jest.mock('@/lib/aws/lambda-client')
import { invokeLambda } from '@/lib/aws/lambda-client'

describe('POST /api/guardian/ml/patterns', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('returns 400 when threats array is missing', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/patterns'),
      {
        method: 'POST',
        body: JSON.stringify({
          min_support: 0.3
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(400)
  })

  it('returns 400 when threats is not an array', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/patterns'),
      {
        method: 'POST',
        body: JSON.stringify({
          threats: 'not an array',
          min_support: 0.3
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(400)
  })

  it('identifies patterns with correct parameters', async () => {
    const mockResponse = {
      statusCode: 200,
      body: JSON.stringify({
        patterns: [
          {
            id: 'P1',
            sequence: ['Unknown Region', 'Unauthorized SSH'],
            support: 0.4,
            confidence: 0.8,
            lift: 2.0,
            occurrences: 2
          }
        ],
        total_patterns: 1,
        threat_count: 5
      })
    }

    ;(invokeLambda as jest.Mock).mockResolvedValue(mockResponse)

    const threats = [
      { threat_type: 'Unknown Region', timestamp: '2026-05-26T00:00:00' },
      { threat_type: 'Unauthorized SSH', timestamp: '2026-05-26T01:00:00' },
      { threat_type: 'Data Exfil', timestamp: '2026-05-26T02:00:00' },
      { threat_type: 'Unknown Region', timestamp: '2026-05-26T03:00:00' },
      { threat_type: 'Unauthorized SSH', timestamp: '2026-05-26T04:00:00' }
    ]

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/patterns'),
      {
        method: 'POST',
        body: JSON.stringify({
          threats,
          min_support: 0.3
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(200)
    expect(invokeLambda).toHaveBeenCalledWith('ml_patterns', expect.objectContaining({
      threats,
      min_support: 0.3
    }))

    const json = await response.json()
    expect(json.total_patterns).toBe(1)
    expect(json.patterns[0].sequence).toContain('Unknown Region')
  })

  it('defaults min_support to 0.3 if not provided', async () => {
    const mockResponse = {
      statusCode: 200,
      body: JSON.stringify({
        patterns: [],
        total_patterns: 0,
        threat_count: 5
      })
    }

    ;(invokeLambda as jest.Mock).mockResolvedValue(mockResponse)

    const threats = [
      { threat_type: 'Unknown Region', timestamp: '2026-05-26T00:00:00' }
    ]

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/patterns'),
      {
        method: 'POST',
        body: JSON.stringify({
          threats
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(200)
    expect(invokeLambda).toHaveBeenCalledWith('ml_patterns', expect.objectContaining({
      min_support: 0.3
    }))
  })

  it('returns pattern metrics with confidence and lift', async () => {
    const mockResponse = {
      statusCode: 200,
      body: JSON.stringify({
        patterns: [
          {
            id: 'P1',
            sequence: ['Login Anomaly', 'Data Access', 'Exfiltration'],
            support: 0.35,
            confidence: 0.92,
            lift: 3.5,
            occurrences: 7
          },
          {
            id: 'P2',
            sequence: ['Permission Escalation', 'Admin Access'],
            support: 0.25,
            confidence: 0.78,
            lift: 2.1,
            occurrences: 5
          }
        ],
        total_patterns: 2,
        threat_count: 20
      })
    }

    ;(invokeLambda as jest.Mock).mockResolvedValue(mockResponse)

    const threats = Array(20).fill(null).map((_, i) => ({
      threat_type: `Threat${i % 5}`,
      timestamp: new Date(Date.now() - i * 3600000).toISOString()
    }))

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/patterns'),
      {
        method: 'POST',
        body: JSON.stringify({
          threats,
          min_support: 0.25
        })
      }
    )

    const response = await POST(request)
    const json = await response.json()
    expect(json.total_patterns).toBe(2)
    expect(json.patterns[0].confidence).toBe(0.92)
    expect(json.patterns[1].lift).toBe(2.1)
  })
})
