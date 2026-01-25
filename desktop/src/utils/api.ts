import { invoke } from '@tauri-apps/api/tauri'
import type { PredictionResult, BatchResult, ModelInfo } from '../types'

let backendUrl: string | null = null

export async function getBackendUrl(): Promise<string> {
  if (!backendUrl) {
    try {
      // Try to get from Tauri command (production)
      backendUrl = await invoke<string>('get_backend_url')
    } catch (e) {
      // Fall back to localhost in development
      console.warn('Using fallback backend URL for development')
      backendUrl = 'http://127.0.0.1:8008'
    }
  }
  return backendUrl
}

export async function getModelInfo(): Promise<ModelInfo> {
  const url = await getBackendUrl()
  const response = await fetch(`${url}/model/info`)
  if (!response.ok) throw new Error(`Failed to fetch model info: ${response.statusText}`)
  return response.json()
}

export async function analyzeImage(
  imagePath: string,
  returnOverlay: boolean = true
): Promise<PredictionResult> {
  const url = await getBackendUrl()
  const response = await fetch(`${url}/infer/image`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_path: imagePath,
      return_overlay_png: returnOverlay,
    }),
  })
  if (!response.ok) throw new Error(`Inference failed: ${response.statusText}`)
  return response.json()
}

export async function analyzeFolder(
  folderPath: string,
  returnOverlay: boolean = true,
  limit?: number,
  profileId?: string,
  profileName?: string
): Promise<BatchResult> {
  const url = await getBackendUrl()
  const response = await fetch(`${url}/infer/folder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      folder_path: folderPath,
      recursive: true,
      return_overlay_png: returnOverlay,
      limit: limit || null,
      profile_id: profileId || null,
      profile_name: profileName || null,
    }),
  })
  if (!response.ok) throw new Error(`Batch inference failed: ${response.statusText}`)
  return response.json()
}

export async function exportCSV(
  outputPath: string,
  predictions: PredictionResult[]
): Promise<void> {
  const url = await getBackendUrl()
  const response = await fetch(`${url}/export/csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      output_path: outputPath,
      predictions,
    }),
  })
  if (!response.ok) throw new Error(`CSV export failed: ${response.statusText}`)
}

export async function exportJSON(
  outputPath: string,
  predictions: PredictionResult[]
): Promise<void> {
  const url = await getBackendUrl()
  const response = await fetch(`${url}/export/json`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      output_path: outputPath,
      predictions,
    }),
  })
  if (!response.ok) throw new Error(`JSON export failed: ${response.statusText}`)
}

export async function exportAnnotatedImages(
  outputDir: string,
  predictions: PredictionResult[],
  suffix: string = '_annotated'
): Promise<void> {
  const url = await getBackendUrl()
  const response = await fetch(`${url}/export/annotated-images`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      output_dir: outputDir,
      predictions,
      suffix,
    }),
  })
  if (!response.ok) throw new Error(`Image export failed: ${response.statusText}`)
}
