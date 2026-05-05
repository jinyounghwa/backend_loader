import { POST } from '@/app/api/analyze-threat/route'
import { NextRequest } from 'next/server'
import * as authUtils from '@/lib/auth-utils'

jest.mock('@google/generative-ai', () => ({
  GoogleGenerativeAI: jest.fn(() => ({
    getGenerativeModel: jest.fn(() => ({
      generateContent: jest.fn().mockRejectedValue(new Error('API Error')),
    })),
  })),
}))
jest.mock('@/lib/auth-utils')

describe('POST /api/analyze-threat', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Mock authenticated session by default
    ;(authUtils.getAuthSession as jest.Mock).mockResolvedValue({
      user: { email: 'admin@localhost', name: 'Local Admin', role: 'admin' },
      expires: new Date(Date.now() + 86400000).toISOString(),
    })
    // Ensure GOOGLE_API_KEY is not set by default
    delete process.env.GOOGLE_API_KEY
  })

  it('returns 401 when not authenticated', async () => {
    ;(authUtils.getAuthSession as jest.Mock).mockResolvedValue(null)

    const request = new NextRequest(new URL('http://localhost:3000/api/analyze-threat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events: [{ event_type: 'ec2', severity: 'critical' }] }),
    })

    const response = await POST(request)
    expect(response.status).toBe(401)
  })

  it('returns 400 when body is empty', async () => {
    const request = new NextRequest(new URL('http://localhost:3000/api/analyze-threat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })

    const response = await POST(request)
    expect(response.status).toBe(400)
  })

  it('returns 400 when events array is empty', async () => {
    const request = new NextRequest(new URL('http://localhost:3000/api/analyze-threat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events: [] }),
    })

    const response = await POST(request)
    expect(response.status).toBe(400)
  })

  it('returns MOCK_ANALYSIS when no GOOGLE_API_KEY is set', async () => {
    // Ensure API key is not set
    delete process.env.GOOGLE_API_KEY

    const request = new NextRequest(new URL('http://localhost:3000/api/analyze-threat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        events: [{ event_type: 'ec2', severity: 'critical' }],
      }),
    })

    const response = await POST(request)
    expect(response.status).toBe(200)

    const json = await response.json()
    expect(json.severity).toBeDefined()
    expect(json.rootCause).toBeDefined()
    expect(json.remediationSteps).toBeDefined()
    expect(json.preventionTips).toBeDefined()
  })

  it('returns MOCK_ANALYSIS when Gemini API throws error', async () => {
    // Set fake API key to trigger Gemini path
    process.env.GOOGLE_API_KEY = 'fake-key-for-testing'

    const request = new NextRequest(new URL('http://localhost:3000/api/analyze-threat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        events: [
          { event_type: 'ec2', severity: 'critical' },
          { event_type: 's3', severity: 'warning' },
        ],
      }),
    })

    const response = await POST(request)
    expect(response.status).toBe(200)

    const json = await response.json()
    // Should return mock analysis as fallback when API throws
    expect(json.severity).toBeDefined()

    // Clean up
    delete process.env.GOOGLE_API_KEY
  })

  it('accepts POST request with valid threat events', async () => {
    const request = new NextRequest(new URL('http://localhost:3000/api/analyze-threat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        events: [
          {
            event_type: 'ec2',
            severity: 'critical',
            resource_id: 'i-123456',
            details: { exposed_ports: [22, 3389] },
          },
        ],
      }),
    })

    const response = await POST(request)
    expect(response.status).toBe(200)

    const json = await response.json()
    expect(json).toHaveProperty('severity')
    expect(json).toHaveProperty('rootCause')
  })
})
