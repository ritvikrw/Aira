const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

/** Returns true if the string contains any Indian-script Unicode characters. */
export function hasIndianScript(text: string): boolean {
  if (!text) return false
  for (const char of text) {
    const cp = char.codePointAt(0) ?? 0
    if (
      (cp >= 0x0900 && cp <= 0x097F) || // Devanagari (Hindi / Marathi)
      (cp >= 0x0980 && cp <= 0x09FF) || // Bengali
      (cp >= 0x0A00 && cp <= 0x0A7F) || // Gurmukhi (Punjabi)
      (cp >= 0x0A80 && cp <= 0x0AFF) || // Gujarati
      (cp >= 0x0B00 && cp <= 0x0B7F) || // Odia
      (cp >= 0x0B80 && cp <= 0x0BFF) || // Tamil
      (cp >= 0x0C00 && cp <= 0x0C7F) || // Telugu
      (cp >= 0x0C80 && cp <= 0x0CFF) || // Kannada
      (cp >= 0x0D00 && cp <= 0x0D7F)    // Malayalam
    ) return true
  }
  return false
}

/**
 * Batch-translate an array of strings to English.
 * Strings that are already in English are returned as-is.
 * Falls back to originals on any network/API error.
 */
export async function translateToEnglish(texts: string[]): Promise<string[]> {
  if (!texts.length) return texts
  if (!texts.some(t => hasIndianScript(t))) return texts   // nothing to translate

  try {
    const res = await fetch(`${API}/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts }),
    })
    if (!res.ok) return texts
    const data = await res.json()
    return (data.translations as string[]) ?? texts
  } catch {
    return texts
  }
}
