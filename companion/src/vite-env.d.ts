/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_HERMES_BASE_URL: string
  readonly VITE_HERMES_API_KEY: string
  readonly VITE_VOICE_BASE_URL: string
  readonly VITE_AGENT_NAME: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
