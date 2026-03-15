import { invoke } from '@tauri-apps/api/tauri'
import { fetch as tauriFetch, ResponseType, Body } from '@tauri-apps/api/http'
import type { PredictionResult, BatchResult, ModelInfo } from '../types'

let backendUrl: string | null = null

export function resetBackendUrl() {
  backendUrl = null
}

export async function getBackendUrl(): Promise<string> {
  if (!backendUrl) {
    try {
      // Try to get from Tauri command (production)
      const url = await invoke<string>('get_backend_url')
      // Only cache non-empty URLs
      if (url && url.length > 0) {
        backendUrl = url
      } else {
        return 'http://127.0.0.1:8008'
      }
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
  console.log('Fetching model info from:', `${url}/model/info`)
  
  try {
    const response = await tauriFetch(`${url}/model/info`, {
      method: 'GET',
      responseType: ResponseType.JSON
    })
    console.log('Model info response:', response)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch model info: ${response.status}`)
    }
    return response.data as ModelInfo
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
  const response = await tauriFetch(`${url}/infer/image`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    responseType: ResponseType.JSON,
    body: Body.json({
      image_path: imagePath,
      return_overlay_png: returnOverlay,
    }),
  })
  if (!response.ok) throw new Error(`Inference failed: ${response.status}`)
  return response.data as PredictionResult
}

export async function analyzeFolder(
  folderPath: string,
  returnOverlay: boolean = true,
  limit?: number,
  profileId?: string,
  profileName?: string
): Promise<BatchResult> {
  const url = await getBackendUrl()
  const response = await tauriFetch(`${url}/infer/folder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    responseType: ResponseType.JSON,
    body: Body.json({
      folder_path: folderPath,
      recursive: true,
      return_overlay_png: returnOverlay,
      limit: limit || null,
      profile_id: profileId || null,
      profile_name: profileName || null,
    }),
  })
  if (!response.ok) throw new Error(`Batch inference failed: ${response.status}`)
  return response.data as BatchResult
}

export async function exportCSV(
  outputPath: string,
  predictions: PredictionResult[]
): Promise<void> {
  const url = await getBackendUrl()
  const response = await tauriFetch(`${url}/export/csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    responseType: ResponseType.JSON,
    body: Body.json({
      output_path: outputPath,
      predictions,
    }),
  })
  if (!response.ok) throw new Error(`CSV export failed: ${response.status}`)
}

export async function exportJSON(
  outputPath: string,
  predictions: PredictionResult[]
): Promise<void> {
  const url = await getBackendUrl()
  const response = await tauriFetch(`${url}/export/json`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    responseType: ResponseType.JSON,
    body: Body.json({
      output_path: outputPath,
      predictions,
    }),
  })
  if (!response.ok) throw new Error(`JSON export failed: ${response.status}`)
}

export async function exportAnnotatedImages(
  outputDir: string,
  predictions: PredictionResult[],
  suffix: string = '_annotated'
): Promise<void> {
  const url = await getBackendUrl()
  const response = await tauriFetch(`${url}/export/annotated-images`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    responseType: ResponseType.JSON,
    body: Body.json({
      output_dir: outputDir,
      predictions,
      suffix,
    }),
  })
  if (!response.ok) throw new Error(`Image export failed: ${response.status}`)
}
