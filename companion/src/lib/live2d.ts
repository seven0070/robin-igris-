import { Application, Ticker } from 'pixi.js'
import { Live2DModel } from 'pixi-live2d-display/cubism4'

// Register ticker for pixi-live2d-display (AIRI / Cubism4 path)
Live2DModel.registerTicker(Ticker)

export type Live2DHandle = {
  setMouthOpen: (value: number) => void
  destroy: () => void
}

/**
 * Mount AIRI's Hiyori Free Live2D model (downloaded via @proj-airi/unplugin-fetch).
 * Cubism core is provided by @proj-airi/unplugin-live2d-sdk — same pipeline as moeru-ai/airi.
 */
export async function mountLive2D(canvas: HTMLCanvasElement): Promise<Live2DHandle> {
  const app = new Application({
    view: canvas,
    resizeTo: canvas.parentElement || window,
    backgroundAlpha: 0,
    antialias: true,
    resolution: Math.min(window.devicePixelRatio || 1, 2),
    autoDensity: true,
  })

  // Model zip is unpacked / served under public assets by unplugin-fetch.
  // Prefer extracted folder entry if present; otherwise zip URL.
  const candidates = [
    '/assets/live2d/models/hiyori_free_zh/runtime/hiyori_free_t08.model3.json',
    '/assets/live2d/models/hiyori_free_zh.zip',
  ]

  let model: Live2DModel | null = null
  let lastError: unknown
  for (const url of candidates) {
    try {
      model = await Live2DModel.from(url, { autoInteract: false })
      break
    } catch (err) {
      lastError = err
    }
  }
  if (!model) {
    throw lastError || new Error('Failed to load Live2D model')
  }

  app.stage.addChild(model)
  const layout = () => {
    const w = app.renderer.width
    const h = app.renderer.height
    const scale = Math.min(w / model!.width, h / model!.height) * 0.92
    model!.scale.set(scale)
    model!.x = w / 2
    model!.y = h * 0.98
    model!.anchor.set(0.5, 1)
  }
  layout()
  window.addEventListener('resize', layout)

  const core = (model.internalModel as { coreModel?: { setParameterValueById: (id: string, v: number) => void } })
    .coreModel

  return {
    setMouthOpen(value: number) {
      const v = Math.max(0, Math.min(1, value))
      try {
        core?.setParameterValueById('ParamMouthOpenY', v)
      } catch {
        // some models use different ids
        try {
          core?.setParameterValueById('ParamMouthOpen', v)
        } catch {
          /* ignore */
        }
      }
    },
    destroy() {
      window.removeEventListener('resize', layout)
      model?.destroy()
      app.destroy(true)
    },
  }
}
