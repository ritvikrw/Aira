const { formatDuration, formatPhone } = require('../frontend/src/lib/utils')

describe('formatDuration', () => {
  test('formatDuration(0) returns "0s"', () => {
    expect(formatDuration(0)).toBe('0s')
  })
  test('formatDuration(45) returns "45s"', () => {
    expect(formatDuration(45)).toBe('45s')
  })
  test('formatDuration(60) returns "1m"', () => {
    expect(formatDuration(60)).toBe('1m')
  })
  test('formatDuration(90) returns "1m 30s"', () => {
    expect(formatDuration(90)).toBe('1m 30s')
  })
  test('formatDuration(3600) returns "60m"', () => {
    expect(formatDuration(3600)).toBe('60m')
  })
})

describe('formatPhone', () => {
  test('formatPhone("") returns "Unknown"', () => {
    expect(formatPhone('')).toBe('Unknown')
  })
  test('formatPhone("+919876543210") returns "+91 98765 43210"', () => {
    expect(formatPhone('+919876543210')).toBe('+91 98765 43210')
  })
  test('formatPhone("+1234567890") returns "+1234567890" (no transform)', () => {
    expect(formatPhone('+1234567890')).toBe('+1234567890')
  })
})
