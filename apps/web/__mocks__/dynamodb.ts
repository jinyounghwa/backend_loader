// Mock all DynamoDB exports
// This prevents real AWS calls during tests

export const ddbItemToGuardianEvent = jest.fn((item, index) => ({
  event_id: `evt-${index}`,
  event_type: 'ec2',
  severity: 'critical',
  timestamp: new Date().toISOString(),
  details: {},
}))

export const docClient = {
  send: jest.fn().mockResolvedValue({ Items: [] }),
}

export const getLatestCheckResult = jest.fn().mockResolvedValue(null)

export const getRecentEvents = jest.fn().mockResolvedValue([])

export const getEventsByGSI = jest.fn().mockResolvedValue([])

export const getEventsByType = jest.fn().mockResolvedValue([])

export const getEventsBySeverity = jest.fn().mockResolvedValue([])

export const getLatestCheckResultOptimized = jest.fn().mockResolvedValue(null)
