/** Talk to Hermes / USB voice bridge (same-origin on pendrive mode). */

const hermesBase = () =>
  (import.meta.env.VITE_HERMES_BASE_URL || '/hermes/v1').replace(/\/$/, '')

const hermesKey = () => import.meta.env.VITE_HERMES_API_KEY || 'robin-igris-dev'

export type ChatMessage = { role: 'system' | 'user' | 'assistant'; content: string }

export async function hermesChat(
  messages: ChatMessage[],
  opts: { signal?: AbortSignal } = {},
): Promise<string> {
  const endpoints = ['/v1/chat/completions', `${hermesBase()}/chat/completions`]
  let lastErr: Error | null = null
  for (const url of endpoints) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        signal: opts.signal,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${hermesKey()}`,
          'X-Hermes-Session-Key': 'robin-igris-companion',
        },
        body: JSON.stringify({
          model: 'hermes-agent',
          messages,
          temperature: 0.5,
        }),
      })
      if (!res.ok) {
        const text = await res.text()
        lastErr = new Error(`Chat ${res.status}: ${text.slice(0, 240)}`)
        continue
      }
      const data = await res.json()
      return data?.choices?.[0]?.message?.content?.trim() || ''
    } catch (err) {
      lastErr = err instanceof Error ? err : new Error(String(err))
    }
  }
  throw lastErr || new Error('No chat endpoint available')
}

export async function hermesHealth(): Promise<boolean> {
  try {
    const res = await fetch('/health')
    if (res.ok) {
      const data = await res.json()
      return Boolean(data?.ok)
    }
  } catch {
    /* fall through */
  }
  try {
    const base = hermesBase().replace(/\/v1$/, '')
    const res = await fetch(`${base}/health`, {
      headers: { Authorization: `Bearer ${hermesKey()}` },
    })
    return res.ok
  } catch {
    return false
  }
}
