const { hasIndianScript, translateToEnglish } = require('../frontend/src/lib/translate')

describe('hasIndianScript', () => {
  test('empty string returns false', () => {
    expect(hasIndianScript('')).toBe(false)
  })
  test('"hello" returns false', () => {
    expect(hasIndianScript('hello')).toBe(false)
  })
  test('Telugu text returns true', () => {
    expect(hasIndianScript('నమస్కారం')).toBe(true)
  })
  test('Hindi/Devanagari text returns true', () => {
    expect(hasIndianScript('నమస్తే')).toBe(true)
  })
  test('Hindi Devanagari नमस्ते returns true', () => {
    expect(hasIndianScript('నమస్తే')).toBe(true)
  })
})

describe('translateToEnglish', () => {
  test('empty array returns empty array', async () => {
    const result = await translateToEnglish([])
    expect(result).toEqual([])
  })

  test('English-only text is returned as-is without fetch', async () => {
    const result = await translateToEnglish(['hello'])
    expect(result).toEqual(['hello'])
  })

  test('Indian script text calls fetch and returns translations', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ translations: ['Greetings'] }),
    })
    const result = await translateToEnglish(['నమస్కారం'])
    expect(result).toEqual(['Greetings'])
    expect(global.fetch).toHaveBeenCalled()
    delete global.fetch
  })

  test('fetch failure falls back to original texts', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('network error'))
    const result = await translateToEnglish(['నమస్కారం'])
    expect(result).toEqual(['నమస్కారం'])
    delete global.fetch
  })
})
