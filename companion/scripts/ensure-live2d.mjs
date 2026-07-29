#!/usr/bin/env node
/**
 * Ensure AIRI Hiyori Free Live2D model is downloaded + unzipped for the companion.
 * Mirrors @proj-airi/unplugin-fetch destinations used by moeru-ai/airi.
 */
import { createWriteStream, existsSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { pipeline } from 'node:stream/promises'
import { createRequire } from 'node:module'
import { Readable } from 'node:stream'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const yauzl = require('yauzl')
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const zipUrl = 'https://dist.ayaka.moe/live2d-models/hiyori_free_zh.zip'
const zipPath = resolve(root, 'public/assets/live2d/models/hiyori_free_zh.zip')
const marker = resolve(
  root,
  'public/assets/live2d/models/hiyori_free_zh/runtime/hiyori_free_t08.model3.json',
)

async function download() {
  if (existsSync(zipPath)) return
  mkdirSync(dirname(zipPath), { recursive: true })
  console.log('Downloading AIRI Hiyori Free Live2D…')
  const res = await fetch(zipUrl)
  if (!res.ok || !res.body) throw new Error(`download failed: ${res.status}`)
  await pipeline(Readable.fromWeb(res.body), createWriteStream(zipPath))
}

function unzip() {
  if (existsSync(marker)) return Promise.resolve()
  const outRoot = resolve(root, 'public/assets/live2d/models')
  return new Promise((resolvePromise, reject) => {
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
        mkdirSync(dirname(dest), { recursive: true })
        zip.openReadStream(entry, (e, stream) => {
          if (e || !stream) return reject(e || new Error('stream failed'))
          const out = createWriteStream(dest)
          stream.pipe(out)
          out.on('finish', () => zip.readEntry())
          out.on('error', reject)
        })
      })
      zip.on('end', () => {
        console.log('Unzipped hiyori_free_zh')
        resolvePromise()
      })
      zip.on('error', reject)
    })
  })
}

await download()
await unzip()
