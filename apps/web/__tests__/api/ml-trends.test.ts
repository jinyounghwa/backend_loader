import { GET } from '@/app/api/guardian/ml/trends/route'
import { NextRequest } from 'next/server'

jest.mock('@/lib/aws/lambda-client')
import { invokeLambda } from '@/lib/aws/lambda-client'

describe('GET /api/guardian/ml/trends', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('returns 400 when account_id is missing', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/trends'),
      { method: 'GET' }
    )

    const response = await GET(request)
    expect(response.status).toBe(400)
  })

  it('queries trends with default time_range', async () => {
    const mockResponse = {
      statusCode: 200,
      body: JSON.stringify({
        hourly_breakdown: [
          { hour: '2026-05-26T00', threats: 5, avg_severity: 6.2 }
        ],
        daily_breakdown: [],
        peak_hours: ['2026-05-26T00'],
        safe_hours: ['2026-05-26T02'],
        anomaly_hours: [],
        trend: 'stable',
        time_range: '24h'
      })
    }

    ;(invokeLambda as jest.Mock).mockResolvedValue(mockResponse)

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/trends?account_id=test-account'),
      { method: 'GET' }
    )

    const response = await GET(request)
    expect(response.status).toBe(200)
    expect(invokeLambda).toHaveBeenCalledWith('ml_trends', expect.objectContaining({
      account_id: 'test-account',
      time_range: '24h'
    }))
  })

  it('respects custom time_range parameter', async () => {
    const mockResponse = {
      statusCode: 200,
      body: JSON.stringify({
        hourly_breakdown: [],
        daily_breakdown: [
          { day: '2026-05-26', threats: 50, avg_severity: 6.5 }
        ],
        peak_hours: [],
        safe_hours: [],
        anomaly_hours: [],
        trend: 'decreasing',
        time_range: '7d'
      })
    }

    ;(invokeLambda as jest.Mock).mockResolvedValue(mockResponse)

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/trends?account_id=test-account&time_range=7d'),
      { method: 'GET' }
    )

    const response = await GET(request)
    expect(response.status).toBe(200)
    expect(invokeLambda).toHaveBeenCalledWith('ml_trends', expect.objectContaining({
      time_range: '7d'
    }))

    const json = await response.json()
    expect(json.time_range).toBe('7d')
    expect(json.trend).toBe('decreasing')
  })

  it('returns hourly and anomaly analysis', async () => {
    const mockResponse = {
      statusCode: 200,
      body: JSON.stringify({
        hourly_breakdown: [
          { hour: '2026-05-26T00', threats: 5, avg_severity: 6.2 },
          { hour: '2026-05-26T01', threats: 3, avg_severity: 5.8 }
        ],
        daily_breakdown: [],
        peak_hours: ['2026-05-26T00'],
        safe_hours: ['2026-05-26T02', '2026-05-26T03'],
        anomaly_hours: ['2026-05-26T12'],
        trend: 'stable'
      })
    }

    ;(invokeLambda as jest.Mock).mockResolvedValue(mockResponse)

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/trends?account_id=test-account'),
      { method: 'GET' }
    )

    const response = await GET(request)
    const json = await response.json()
    expect(json.peak_hours).toContain('2026-05-26T00')
    expect(json.safe_hours).toHaveLength(2)
    expect(json.anomaly_hours).toContain('2026-05-26T12')
  })
})
