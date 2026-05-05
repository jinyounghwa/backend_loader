// Set localstack mode by default for tests
// This bypasses NextAuth and returns a hardcoded local session
process.env.AWS_ENV = 'localstack'
