// Mock shim for @auth module alias
// This is used when AWS_ENV is unset and we need to mock NextAuth
export const auth = jest.fn().mockResolvedValue(null)
