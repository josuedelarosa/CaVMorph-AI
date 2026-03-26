/**
 * Platform abstraction layer.
 *
 * Detects whether the app is running inside Tauri (desktop) or a plain
 * browser (web deployment) and exposes a single API surface that both
 * environments can satisfy.
 *
 * ── Design rule ──────────────────────────────────────────────────────
 * Every public export has the same signature regardless of platform.
 * Consuming code should import from here instead of `@tauri-apps/api/*`.
 * This keeps the Tauri desktop build working exactly as before while
 * enabling a separate `vite build --mode web` for the Docker deployment.
 */

// ── Tauri detection ─────────────────────────────────────────────────
export const isTauri: boolean = !!(window as any).__TAURI__

// ── Resolved backend URL ────────────────────────────────────────────
// In web mode the frontend is served by the same FastAPI process, so
// the API base is simply the page origin (or an explicit env var).
let _cachedBackendUrl: string | null = null

export async function getBackendUrl(): Promise<string> {
  if (_cachedBackendUrl) return _cachedBackendUrl

  if (isTauri) {
    try {
      const { invoke } = await import('@tauri-apps/api/tauri')
      const url = await invoke<string>('get_backend_url')
      if (url && url.length > 0) { _cachedBackendUrl = url; return url }
    } catch { /* fall through */ }
    _cachedBackendUrl = 'http://127.0.0.1:8008'
  } else {
    // Web mode — API is same-origin (FastAPI serves the SPA).
    // When deployed under a sub-path (e.g. /phenoai-web/), Vite sets
    // import.meta.env.BASE_URL to that prefix so API calls go to the
    // right path and nginx can proxy them correctly.
    const base = ((import.meta as any).env?.BASE_URL || '/').replace(/\/$/, '')
    _cachedBackendUrl =
      (import.meta as any).env?.VITE_API_BASE_URL ||
      window.location.origin + base
  }
  return _cachedBackendUrl!
}

export function resetBackendUrl(): void { _cachedBackendUrl = null }

// ── HTTP fetch ──────────────────────────────────────────────────────
// Wraps Tauri fetch (desktop) or native fetch (web).

interface PlatformResponse<T = any> {
  ok: boolean
  status: number
  data: T
}

export async function platformFetch<T = any>(
  url: string,
  options: {
    method?: string
    headers?: Record<string, string>
    body?: any          // plain object — will be JSON-stringified
    timeout?: number    // seconds (Tauri only)
    responseType?: 'json' | 'text' | 'blob'
  } = {},
): Promise<PlatformResponse<T>> {
  const method = options.method ?? 'GET'
  const responseType = options.responseType ?? 'json'

  if (isTauri) {
    const { fetch: tauriFetch, ResponseType, Body } = await import('@tauri-apps/api/http')
    const tauriOpts: any = {
      method,
      responseType: responseType === 'json' ? ResponseType.JSON
                   : responseType === 'blob' ? ResponseType.Binary
                   : ResponseType.Text,
    }
    if (options.headers) tauriOpts.headers = options.headers
    if (options.body !== undefined) {
      tauriOpts.headers = { ...tauriOpts.headers, 'Content-Type': 'application/json' }
      tauriOpts.body = Body.json(options.body)
    }
    if (options.timeout) tauriOpts.timeout = options.timeout
    const resp = await tauriFetch(url, tauriOpts)
    return { ok: resp.ok, status: resp.status, data: resp.data as T }
  }

  // ── Web fetch ───────────────────────────────────────────────────
  const init: RequestInit = { method }
  if (options.headers) init.headers = options.headers
  if (options.body !== undefined) {
    init.headers = { ...(init.headers as any), 'Content-Type': 'application/json' }
    init.body = JSON.stringify(options.body)
  }
  const resp = await fetch(url, init)
  let data: any
  if (responseType === 'json') data = await resp.json()
  else if (responseType === 'blob') data = await resp.blob()
  else data = await resp.text()
  return { ok: resp.ok, status: resp.status, data }
}

// ── File dialog ─────────────────────────────────────────────────────
// Tauri: native OS dialog.  Web: hidden <input type="file">.
// Returns selected absolute paths (Tauri) or uploaded-path strings (web).

export interface DialogOptions {
  directory?: boolean
  multiple?: boolean
  defaultPath?: string
  filters?: { name: string; extensions: string[] }[]
}

export async function openDialog(
  opts: DialogOptions = {},
): Promise<string | string[] | null> {
  if (isTauri) {
    const { open } = await import('@tauri-apps/api/dialog')
    return open(opts as any)
  }

  // ── Web: trigger a hidden <input> ────────────────────────────
  return new Promise((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    if (opts.directory) {
      input.setAttribute('webkitdirectory', '')
      input.setAttribute('directory', '')
    }
    if (opts.multiple) input.multiple = true
    if (opts.filters?.length) {
      input.accept = opts.filters
        .flatMap(f => f.extensions.map(e => `.${e}`))
        .join(',')
    }
    input.style.display = 'none'
    document.body.appendChild(input)

    input.addEventListener('change', async () => {
      document.body.removeChild(input)
      const files = input.files
      if (!files || files.length === 0) { resolve(null); return }

      // Upload files to the backend and return server paths
      const formData = new FormData()
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i])
      }
      try {
        const base = await getBackendUrl()
        const resp = await fetch(`${base}/upload`, { method: 'POST', body: formData })
        if (!resp.ok) { resolve(null); return }
        const json = await resp.json()
        // json = { upload_dir: string, files: [{name, path, size}] }
        if (opts.directory) {
          resolve(json.upload_dir as string)
        } else if (opts.multiple) {
          resolve(json.files.map((f: any) => f.path) as string[])
        } else {
          resolve(json.files[0]?.path ?? null)
        }
      } catch (err) {
        console.error('[platform] Upload failed:', err)
        resolve(null)
      }
    })

    // User cancelled
    input.addEventListener('cancel', () => {
      document.body.removeChild(input)
      resolve(null)
    })

    input.click()
  })
}

// ── Filesystem helpers ──────────────────────────────────────────────

export async function readBinaryFile(path: string): Promise<Uint8Array> {
  if (isTauri) {
    const { readBinaryFile: tauriRead } = await import('@tauri-apps/api/fs')
    return new Uint8Array(await tauriRead(path))
  }
  // Web: fetch the file from the backend serve endpoint
  const base = await getBackendUrl()
  const resp = await fetch(`${base}/files?path=${encodeURIComponent(path)}`)
  if (!resp.ok) throw new Error(`Failed to read file: ${resp.status}`)
  return new Uint8Array(await resp.arrayBuffer())
}

export async function readTextFile(path: string): Promise<string> {
  if (isTauri) {
    const { readTextFile: tauriRead } = await import('@tauri-apps/api/fs')
    return tauriRead(path)
  }
  const bytes = await readBinaryFile(path)
  return new TextDecoder().decode(bytes)
}

export async function writeTextFile(path: string, content: string): Promise<void> {
  if (isTauri) {
    const { writeTextFile: tauriWrite } = await import('@tauri-apps/api/fs')
    return tauriWrite(path, content)
  }
  // Web: no filesystem — handled at caller level (storage.ts uses localStorage)
}

export async function createDir(path: string, opts?: { recursive?: boolean }): Promise<void> {
  if (isTauri) {
    const { createDir: tauriMkdir } = await import('@tauri-apps/api/fs')
    return tauriMkdir(path, opts)
  }
  // Web: no-op
}

// ── Paths ───────────────────────────────────────────────────────────

export async function appDataDir(): Promise<string> {
  if (isTauri) {
    const { appDataDir: tauriAppDataDir } = await import('@tauri-apps/api/path')
    return tauriAppDataDir()
  }
  return '/phenoai-data/'  // placeholder, web mode uses localStorage
}

export async function homeDir(): Promise<string> {
  if (isTauri) {
    const { homeDir: tauriHomeDir } = await import('@tauri-apps/api/path')
    return tauriHomeDir()
  }
  return '/'  // placeholder, web exports use download links
}

// ── Shell / external links ──────────────────────────────────────────

export async function openExternal(url: string): Promise<void> {
  if (isTauri) {
    const { open } = await import('@tauri-apps/api/shell')
    return open(url)
  }
  window.open(url, '_blank', 'noopener')
}

// ── Image URL resolution ────────────────────────────────────────────
// Converts a server-side image path to a URL the <img> tag can load.

export async function resolveImageUrl(imagePath: string): Promise<string> {
  if (isTauri) {
    const { convertFileSrc } = await import('@tauri-apps/api/tauri')
    return convertFileSrc(imagePath)
  }
  const base = await getBackendUrl()
  return `${base}/files?path=${encodeURIComponent(imagePath)}`
}

// ── Tauri invoke (desktop only) ─────────────────────────────────────

export async function tauriInvoke<T = any>(command: string, args?: any): Promise<T> {
  if (!isTauri) throw new Error(`invoke('${command}') is not available in web mode`)
  const { invoke } = await import('@tauri-apps/api/tauri')
  return invoke<T>(command, args)
}

// ── Tauri event listener (desktop only) ─────────────────────────────

export async function tauriListen(event: string, handler: (payload: any) => void): Promise<() => void> {
  if (!isTauri) return () => {}  // no-op in web mode
  const { listen } = await import('@tauri-apps/api/event')
  const unlisten = await listen(event, (ev: any) => handler(ev.payload))
  return unlisten
}
