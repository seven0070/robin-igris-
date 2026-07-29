<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { hermesChat, hermesHealth, type ChatMessage } from './lib/hermes'
import { canUseSpeechRecognition, listenOnce, playWithLipSync, synthesizeSpeech } from './lib/voice'
import { mountLive2D, type Live2DHandle } from './lib/live2d'

const name = import.meta.env.VITE_AGENT_NAME || 'Robin Igris'
const canvasRef = ref<HTMLCanvasElement | null>(null)
const input = ref('')
const busy = ref(false)
const listening = ref(false)
const status = ref('booting…')
const hermesOk = ref(false)
const log = ref<{ role: 'user' | 'assistant'; text: string }[]>([])
const scrollEl = ref<HTMLElement | null>(null)

let live2d: Live2DHandle | null = null
const history: ChatMessage[] = [
  {
    role: 'system',
    content:
      `You are ${name}. Keep replies concise and speakable for voice. ` +
      'You run on Hermes Agent; use tools when helpful. Avoid heavy markdown when voice may be on.',
  },
]

const canTalk = computed(() => canUseSpeechRecognition())

async function refreshHealth() {
  hermesOk.value = await hermesHealth()
  status.value = hermesOk.value
    ? 'Hermes online · avatar ready'
    : 'Hermes offline — start `hermes gateway` (API server)'
}

onMounted(async () => {
  await refreshHealth()
  const timer = window.setInterval(refreshHealth, 8000)
  onUnmounted(() => clearInterval(timer))

  try {
    if (canvasRef.value) {
      live2d = await mountLive2D(canvasRef.value)
      status.value = hermesOk.value
        ? 'Hermes online · Live2D ready (AIRI Hiyori)'
        : 'Live2D ready · Hermes offline'
    }
  } catch (err) {
    console.error(err)
    status.value = `Avatar load failed: ${err instanceof Error ? err.message : String(err)}`
  }
})

onUnmounted(() => {
  live2d?.destroy()
  live2d = null
})

async function scrollDown() {
  await nextTick()
  if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
}

async function speakReply(text: string) {
  try {
    const audio = await synthesizeSpeech(text)
    await playWithLipSync(audio, (open) => live2d?.setMouthOpen(open))
  } catch (err) {
    console.warn('TTS skipped', err)
  }
}

async function sendText(text: string) {
  const trimmed = text.trim()
  if (!trimmed || busy.value) return
  busy.value = true
  input.value = ''
  log.value.push({ role: 'user', text: trimmed })
  history.push({ role: 'user', content: trimmed })
  await scrollDown()

  try {
    const reply = await hermesChat(history)
    history.push({ role: 'assistant', content: reply })
    log.value.push({ role: 'assistant', text: reply })
    await scrollDown()
    await speakReply(reply)
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    log.value.push({ role: 'assistant', text: `⚠ ${msg}` })
  } finally {
    busy.value = false
    await scrollDown()
  }
}

async function onSubmit() {
  await sendText(input.value)
}

async function onHoldTalk() {
  if (busy.value || listening.value) return
  if (!canTalk.value) {
    status.value = 'Speech recognition unsupported — type instead'
    return
  }
  listening.value = true
  status.value = 'Listening…'
  try {
    const heard = await listenOnce()
    status.value = hermesOk.value ? 'Hermes online · avatar ready' : status.value
    if (heard) await sendText(heard)
  } catch (err) {
    status.value = `Mic: ${err instanceof Error ? err.message : String(err)}`
  } finally {
    listening.value = false
  }
}
</script>

<template>
  <div class="stage">
    <header class="brand">
      <p class="mark">{{ name }}</p>
      <p class="sub">Hermes brain · AIRI Live2D body</p>
      <p class="status" :data-ok="hermesOk">{{ status }}</p>
    </header>

    <main class="viewport">
      <canvas ref="canvasRef" class="avatar" aria-label="Live2D avatar" />
    </main>

    <section class="dock">
      <div ref="scrollEl" class="log" aria-live="polite">
        <div v-for="(m, i) in log" :key="i" class="bubble" :data-role="m.role">
          <span class="who">{{ m.role === 'user' ? 'You' : name }}</span>
          <p>{{ m.text }}</p>
        </div>
      </div>

      <form class="composer" @submit.prevent="onSubmit">
        <button
          type="button"
          class="talk"
          :disabled="busy"
          :data-on="listening"
          @pointerdown.prevent="onHoldTalk"
        >
          {{ listening ? 'Listening…' : 'Talk' }}
        </button>
        <input
          v-model="input"
          type="text"
          placeholder="Message Robin Igris…"
          :disabled="busy"
          autocomplete="off"
        />
        <button type="submit" class="send" :disabled="busy || !input.trim()">Send</button>
      </form>
    </section>
  </div>
</template>

<style scoped>
.stage {
  min-height: 100%;
  display: grid;
  grid-template-rows: auto 1fr auto;
}

.brand {
  padding: 1.25rem 1.5rem 0.5rem;
  text-align: center;
}

.mark {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.4rem, 6vw, 4rem);
  letter-spacing: 0.02em;
  line-height: 1;
}

.sub {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-weight: 300;
  letter-spacing: 0.04em;
}

.status {
  margin: 0.65rem 0 0;
  font-size: 0.85rem;
  color: var(--danger);
}

.status[data-ok='true'] {
  color: var(--accent);
}

.viewport {
  position: relative;
  min-height: 42vh;
  display: grid;
  place-items: center;
}

.avatar {
  width: min(720px, 100%);
  height: min(64vh, 720px);
  display: block;
}

.dock {
  margin: 0 auto;
  width: min(760px, calc(100% - 1.5rem));
  padding-bottom: 1.25rem;
  display: grid;
  gap: 0.75rem;
}

.log {
  max-height: 28vh;
  overflow: auto;
  padding: 0.75rem;
  border: 1px solid var(--line);
  background: var(--panel);
  backdrop-filter: blur(10px);
  border-radius: 12px;
}

.bubble {
  margin: 0 0 0.85rem;
}

.bubble:last-child {
  margin-bottom: 0;
}

.who {
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 0.2rem;
}

.bubble p {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.45;
}

.bubble[data-role='assistant'] .who {
  color: var(--accent-2);
}

.composer {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.5rem;
}

.composer input {
  border: 1px solid var(--line);
  background: rgba(8, 12, 24, 0.7);
  color: var(--ink);
  border-radius: 999px;
  padding: 0.85rem 1.1rem;
  outline: none;
}

.composer input:focus {
  border-color: rgba(110, 224, 192, 0.55);
}

.talk,
.send {
  border: 0;
  border-radius: 999px;
  padding: 0.85rem 1.15rem;
  cursor: pointer;
  color: #071018;
  background: var(--accent);
  font-weight: 600;
}

.talk[data-on='true'] {
  background: var(--accent-2);
}

.send {
  background: var(--accent-2);
}

button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .composer {
    grid-template-columns: 1fr;
  }
}
</style>
