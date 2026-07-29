/** Talk to Hermes Agent OpenAI-compatible API server. */

const hermesBase = () =>
  (import.meta.env.VITE_HERMES_BASE_URL || '/hermes/v1').replace(/\/$/, '')

const hermesKey = () => import.meta.env.VITE_HERMES_API_KEY || 'robin-igris-dev'

export type ChatMessage = { role: 'system' | 'user' | 'assistant'; content: string }

export async function hermesChat(
  messages: ChatMessage[],
  opts: { signal?: AbortSignal } = {},
): Promise<string> {
  const res = await fetch(`${hermesBase()}/chat/completions`, {
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
    throw new Error(`Hermes ${res.status}: ${text.slice(0, 240)}`)
  }
  const data = await res.json()
  return data?.choices?.[0]?.message?.content?.trim() || ''
}

export async function hermesHealth(): Promise<boolean> {
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
