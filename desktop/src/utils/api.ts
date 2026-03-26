import {
  getBackendUrl as platformGetBackendUrl,
  resetBackendUrl as platformResetBackendUrl,
  platformFetch,
} from './platform'
import type { PredictionResult, BatchResult, ModelInfo } from '../types'

export function resetBackendUrl() {
  platformResetBackendUrl()
}

export async function getBackendUrl(): Promise<string> {
  return platformGetBackendUrl()
}

export async function getModelInfo(): Promise<ModelInfo> {
  const url = await getBackendUrl()
  console.log('Fetching model info from:', `${url}/model/info`)
  
  try {
    const response = await platformFetch<ModelInfo>(`${url}/model/info`, {
      method: 'GET',
    })
    console.log('Model info response:', response)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch model info: ${response.status}`)
    }
    return response.data
  } catch (error) {
    console.error('getModelInfo error:', error)
    throw error
  }
}

export async function analyzeImage(
  imagePath: string,
  returnOverlay: boolean = true
): Promise<PredictionResult> {
  const url = await getBackendUrl()
  const response = await platformFetch<PredictionResult>(`${url}/infer/image`, {
    method: 'POST',
    body: {
      image_path: imagePath,
      return_overlay_png: returnOverlay,
    },
  })
  if (!response.ok) throw new Error(`Inference failed: ${response.status}`)
  return response.data
}

export async function analyzeFolder(
  folderPath: string,
  returnOverlay: boolean = true,
  limit?: number,
  profileId?: string,
  profileName?: string
): Promise<BatchResult> {
  const url = await getBackendUrl()
  const response = await platformFetch<BatchResult>(`${url}/infer/folder`, {
    method: 'POST',
    body: {
      folder_path: folderPath,
      recursive: true,
      return_overlay_png: returnOverlay,
      limit: limit || null,
      profile_id: profileId || null,
      profile_name: profileName || null,
    },
  })
  if (!response.ok) throw new Error(`Batch inference failed: ${response.status}`)
  return response.data
}

export async function exportCSV(
  outputPath: string,
  predictions: PredictionResult[]
): Promise<void> {
  const url = await getBackendUrl()
  const response = await platformFetch(`${url}/export/csv`, {
    method: 'POST',
    body: {
      output_path: outputPath,
      predictions,
    },
  })
  if (!response.ok) throw new Error(`CSV export failed: ${response.status}`)
}

export async function exportJSON(
  outputPath: string,
  predictions: PredictionResult[]
): Promise<void> {
  const url = await getBackendUrl()
  const response = await platformFetch(`${url}/export/json`, {
    method: 'POST',
    body: {
      output_path: outputPath,
      predictions,
    },
  })
  if (!response.ok) throw new Error(`JSON export failed: ${response.status}`)
}

export async function exportAnnotatedImages(
  outputDir: string,
  predictions: PredictionResult[],
  suffix: string = '_annotated'
): Promise<void> {
  const url = await getBackendUrl()
  const response = await platformFetch(`${url}/export/annotated-images`, {
    method: 'POST',
    body: {
      output_dir: outputDir,
      predictions,
      suffix,
    },
  })
  if (!response.ok) throw new Error(`Image export failed: ${response.status}`)
}

// ── Web-only: download export files via the browser ─────────────────
import { isTauri } from './platform'

export async function downloadExport(
  format: 'csv' | 'json' | 'images',
  predictions: PredictionResult[],
  profileName: string = 'results',
): Promise<void> {
  const url = await getBackendUrl()
  const timestamp = new Date().toISOString().slice(0, 10)
  const resp = await fetch(`${url}/export/${format}/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ predictions, profile_name: profileName }),
  })
  if (!resp.ok) throw new Error(`Download failed: ${resp.status}`)

  const blob = await resp.blob()
  const ext = format === 'images' ? 'zip' : format
  const filename = `${profileName}_${timestamp}.${ext}`
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(a.href)
}
