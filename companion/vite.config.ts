import { resolve } from 'node:path'
import { mkdirSync, existsSync, createWriteStream } from 'node:fs'
import { createRequire } from 'node:module'
import { defineConfig, type Plugin } from 'vite'
import Vue from '@vitejs/plugin-vue'
import { Download } from '@proj-airi/unplugin-fetch/vite'
import { DownloadLive2DSDK } from '@proj-airi/unplugin-live2d-sdk/vite'

const require = createRequire(import.meta.url)

/** Unzip AIRI Hiyori Free so pixi-live2d-display can load model3.json directly. */
function unzipHiyori(): Plugin {
  return {
    name: 'unzip-hiyori-live2d',
    async buildStart() {
      const yauzl = require('yauzl') as typeof import('yauzl')
      const zipPath = resolve(__dirname, 'public/assets/live2d/models/hiyori_free_zh.zip')
      const outRoot = resolve(__dirname, 'public/assets/live2d/models')
      const marker = resolve(outRoot, 'hiyori_free_zh/runtime/hiyori_free_t08.model3.json')
      if (!existsSync(zipPath) || existsSync(marker)) return

      await new Promise<void>((resolvePromise, reject) => {
        yauzl.open(zipPath, { lazyEntries: true }, (err, zip) => {
          if (err || !zip) return reject(err || new Error('zip open failed'))
          zip.readEntry()
          zip.on('entry', (entry) => {
            const dest = resolve(outRoot, entry.fileName)
            if (/\/$/.test(entry.fileName)) {
              mkdirSync(dest, { recursive: true })
              zip.readEntry()
              return
            }
            mkdirSync(resolve(dest, '..'), { recursive: true })
            zip.openReadStream(entry, (e, stream) => {
              if (e || !stream) return reject(e || new Error('stream failed'))
              const out = createWriteStream(dest)
              stream.pipe(out)
              out.on('finish', () => zip.readEntry())
              out.on('error', reject)
            })
          })
          zip.on('end', () => resolvePromise())
          zip.on('error', reject)
        })
      })
      console.log('Unzipped hiyori_free_zh Live2D model')
    },
  }
}

// Same Live2D asset pipeline as Project AIRI (moeru-ai/airi)
export default defineConfig({
  plugins: [
    Vue(),
    DownloadLive2DSDK(),
    Download(
      'https://dist.ayaka.moe/live2d-models/hiyori_free_zh.zip',
      'hiyori_free_zh.zip',
      'assets/live2d/models',
    ),
    unzipHiyori(),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    fs: { strict: false },
    proxy: {
      '/hermes': {
        target: 'http://127.0.0.1:8642',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/hermes/, ''),
      },
      '/voice': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/voice/, ''),
      },
    },
  },
  optimizeDeps: {
    exclude: [
      '@framework/live2dcubismframework',
      '@framework/math/cubismmatrix44',
      '@framework/type/csmvector',
      '@framework/math/cubismviewmatrix',
      '@framework/cubismdefaultparameterid',
      '@framework/cubismmodelsettingjson',
      '@framework/effect/cubismbreath',
      '@framework/effect/cubismeyeblink',
      '@framework/model/cubismusermodel',
      '@framework/motion/acubismmotion',
      '@framework/motion/cubismmotionqueuemanager',
      '@framework/type/csmmap',
      '@framework/utils/cubismdebug',
      '@framework/model/cubismmoc',
    ],
  },
})
