import { invoke } from '@tauri-apps/api/core'

export interface EngineInfo {
  port: number
  token: string
}

interface EngineStatus {
  state: 'starting' | 'ready' | 'failed'
  info: EngineInfo | null
  message: string | null
}

let cached: EngineInfo | null = null

export async function engineStatus(): Promise<EngineStatus> {
  return invoke<EngineStatus>('engine_status')
}

export async function restartEngine(): Promise<EngineInfo> {
  cached = null
  const info = await invoke<EngineInfo>('restart_engine')
  cached = info
  return info
}

/** Waits for the engine, but fails fast with a real reason if it broke. */
export async function getEngine(): Promise<EngineInfo> {
  if (cached) return cached
  for (let attempt = 0; attempt < 60; attempt++) {
    const status = await engineStatus()
    if (status.state === 'ready' && status.info) {
      cached = status.info
      return cached
    }
    if (status.state === 'failed') {
      throw new Error(status.message ?? 'The engine failed to start.')
    }
    await new Promise(r => setTimeout(r, 500))
  }
  throw new Error('The engine did not start within 30 seconds.')
}

export async function apiBase(): Promise<string> {
  const { port } = await getEngine()
  return `http://127.0.0.1:${port}/api`
}

export async function wsBase(): Promise<string> {
  const { port } = await getEngine()
  return `ws://127.0.0.1:${port}/api`
}

export async function authHeaders(): Promise<Record<string, string>> {
  const { token } = await getEngine()
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
}

/** Images are stored as `/static/…` because the engine's port changes each
 *  launch. Left relative they'd resolve against the dev server and 404. */
export async function assetUrl(path: string): Promise<string> {
  if (!path || /^https?:\/\//.test(path)) return path
  const { port } = await getEngine()
  return `http://127.0.0.1:${port}${path}`
}
