const nextJest = require('next/jest')
const path = require('path')
const createJestConfig = nextJest({ dir: './' })
module.exports = createJestConfig({
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '\\.(css|less|scss)$': 'identity-obj-proxy',
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  roots: [path.resolve(__dirname, '../tests')],
  testMatch: ['**/*.test.{js,jsx,ts,tsx}'],
  collectCoverageFrom: ['src/**/*.{ts,tsx}', '!src/**/*.d.ts'],
  transformIgnorePatterns: ['/node_modules/(?!(date-fns|lucide-react)/)'],
  modulePaths: [path.resolve(__dirname, 'node_modules')],
  moduleDirectories: ['node_modules', path.resolve(__dirname, 'node_modules')],
})
