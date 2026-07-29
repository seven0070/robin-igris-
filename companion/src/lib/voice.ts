/** Browser STT + server TTS + amplitude mouth driver. */

const voiceBase = () =>
  (import.meta.env.VITE_VOICE_BASE_URL || '').replace(/\/$/, '')

export type MouthDriver = (open: number) => void

export function canUseSpeechRecognition(): boolean {
  return typeof window !== 'undefined' && !!(window.SpeechRecognition || window.webkitSpeechRecognition)
}

declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition
    webkitSpeechRecognition: typeof SpeechRecognition
  }
}

export function listenOnce(lang = 'en-US'): Promise<string> {
  return new Promise((resolve, reject) => {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Ctor) {
      reject(new Error('SpeechRecognition not supported in this browser'))
      return
    }
    const rec = new Ctor()
    rec.lang = lang
    rec.interimResults = false
    rec.maxAlternatives = 1
    rec.onresult = (ev: SpeechRecognitionEvent) => {
      const text = ev.results[0]?.[0]?.transcript?.trim() || ''
      resolve(text)
    }
    rec.onerror = (ev: SpeechRecognitionErrorEvent) => reject(new Error(ev.error || 'stt-failed'))
    rec.start()
  })
}

export async function synthesizeSpeech(text: string): Promise<ArrayBuffer> {
  const res = await fetch(`${voiceBase()}/v1/audio/speech`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input: text, voice: 'alloy', format: 'mp3' }),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`TTS ${res.status}: ${err.slice(0, 200)}`)
  }
  return res.arrayBuffer()
}

export async function playWithLipSync(
  audioData: ArrayBuffer,
  onMouth: MouthDriver,
): Promise<void> {
  const ctx = new AudioContext()
  const buffer = await ctx.decodeAudioData(audioData.slice(0))
  const source = ctx.createBufferSource()
  source.buffer = buffer
  const analyser = ctx.createAnalyser()
  analyser.fftSize = 256
  source.connect(analyser)
  analyser.connect(ctx.destination)

  const data = new Uint8Array(analyser.frequencyBinCount)
  let raf = 0
  const tick = () => {
    analyser.getByteFrequencyData(data)
    // Emphasize mid bands (speech)
    let sum = 0
    const start = 2
    const end = Math.min(24, data.length)
    for (let i = start; i < end; i++) sum += data[i]
    const avg = sum / (end - start)
    onMouth(Math.min(1, avg / 90))
    raf = requestAnimationFrame(tick)
  }

  await ctx.resume()
  tick()
  source.start()
  await new Promise<void>((resolve) => {
    source.onended = () => resolve()
  })
  cancelAnimationFrame(raf)
  onMouth(0)
  await ctx.close()
}
