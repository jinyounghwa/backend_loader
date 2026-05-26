import { POST } from '@/app/api/guardian/ml/predict/route'
import { NextRequest } from 'next/server'

// Mock the lambda client
jest.mock('@/lib/aws/lambda-client', () => ({
  invokeLambda: jest.fn()
}))

import { invokeLambda } from '@/lib/aws/lambda-client'

describe('POST /api/guardian/ml/predict', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('returns 400 when account_id is missing', async () => {
    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/predict'),
      {
        method: 'POST',
        body: JSON.stringify({
          days_ahead: 7
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(400)
    const json = await response.json()
    expect(json.error).toBeDefined()
  })

  it('invokes lambda with correct parameters', async () => {
    const mockResponse = {
      statusCode: 200,
      body: JSON.stringify({
        predictions: [
          { date: '2026-05-27', expected_threats: 2.5, confidence: 0.95 }
        ],
        trend: 'stable',
        anomaly_score: 0.5,
        model_accuracy: 0.85
      })
    }

    ;(invokeLambda as jest.Mock).mockResolvedValue(mockResponse)

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/predict'),
      {
        method: 'POST',
        body: JSON.stringify({
          account_id: 'test-account',
          days_ahead: 7
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(200)
    expect(invokeLambda).toHaveBeenCalledWith('ml_predict', expect.objectContaining({
      account_id: 'test-account',
      days_ahead: 7
    }))
  })

  it('returns lambda response', async () => {
    const mockResponse = {
      statusCode: 200,
      body: JSON.stringify({
        predictions: [
          { date: '2026-05-27', expected_threats: 2.5, confidence: 0.95 }
        ],
        trend: 'increasing',
        anomaly_score: 0.6,
        model_accuracy: 0.88
      })
    }

    ;(invokeLambda as jest.Mock).mockResolvedValue(mockResponse)

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/predict'),
      {
        method: 'POST',
        body: JSON.stringify({
          account_id: 'test-account'
        })
      }
    )

    const response = await POST(request)
    const json = await response.json()
    expect(json.trend).toBe('increasing')
    expect(json.model_accuracy).toBe(0.88)
  })

  it('handles lambda errors gracefully', async () => {
    ;(invokeLambda as jest.Mock).mockRejectedValue(new Error('Lambda error'))

    const request = new NextRequest(
      new URL('http://localhost:3000/api/guardian/ml/predict'),
      {
        method: 'POST',
        body: JSON.stringify({
          account_id: 'test-account'
        })
      }
    )

    const response = await POST(request)
    expect(response.status).toBe(500)
    const json = await response.json()
    expect(json.error).toBeDefined()
  })
})
