import { POST } from '@/app/api/guardian/ml/cluster/route'
import { NextRequest } from 'next/server'

jest.mock('@/lib/aws/lambda-client')
import { invokeLambda } from '@/lib/aws/lambda-client'

describe('POST /api/guardian/ml/cluster', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('returns 400 when threats array is missing', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/cluster'),
      {
        method: 'POST',
        body: JSON.stringify({
          n_clusters: 5
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(400)
  })

  it('returns 400 when threats is not an array', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/cluster'),
      {
        method: 'POST',
        body: JSON.stringify({
          threats: 'not an array',
          n_clusters: 5
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(400)
  })

  it('performs clustering with correct parameters', async () => {
    const mockResponse = {
      statusCode: 200,
      body: JSON.stringify({
        clusters: [
          {
            id: 'C1',
            threats: ['t1', 't2'],
            threat_count: 2,
            cohesion: 0.92,
            avg_severity: 7.5
          }
        ],
        silhouette_score: 0.8,
        cluster_count: 1,
        threat_count: 2
      })
    }

    ;(invokeLambda as jest.Mock).mockResolvedValue(mockResponse)

    const threats = [
      {
        threat_id: 't1',
        severity: 7,
        account_risk_score: 0.75,
        event_frequency: 4,
        resource_impact_count: 2,
        response_time_seconds: 100,
        remediation_success_rate: 0.75
      },
      {
        threat_id: 't2',
        severity: 8,
        account_risk_score: 0.8,
        event_frequency: 5,
        resource_impact_count: 3,
        response_time_seconds: 120,
        remediation_success_rate: 0.7
      }
    ]

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/cluster'),
      {
        method: 'POST',
        body: JSON.stringify({
          threats,
          n_clusters: 1
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(200)
    expect(invokeLambda).toHaveBeenCalledWith('ml_cluster', expect.objectContaining({
      threats,
      n_clusters: 1
    }))

    const json = await response.json()
    expect(json.cluster_count).toBe(1)
    expect(json.silhouette_score).toBe(0.8)
  })

  it('defaults n_clusters to 5 if not provided', async () => {
    const mockResponse = {
      statusCode: 200,
      body: JSON.stringify({
        clusters: [],
        silhouette_score: 0.7,
        cluster_count: 5,
        threat_count: 1
      })
    }

    ;(invokeLambda as jest.Mock).mockResolvedValue(mockResponse)

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/cluster'),
      {
        method: 'POST',
        body: JSON.stringify({
          threats: [
            {
              threat_id: 't1',
              severity: 8,
              account_risk_score: 0.8,
              event_frequency: 5,
              resource_impact_count: 3,
              response_time_seconds: 120,
              remediation_success_rate: 0.7
            }
          ]
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(200)
    expect(invokeLambda).toHaveBeenCalledWith('ml_cluster', expect.objectContaining({
      n_clusters: 5
    }))
  })
})
