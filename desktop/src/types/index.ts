export interface Keypoint {
  x: number
  y: number
  confidence: number
}

export interface Phenotype {
  id: number
  pair: [number, number]
  name: string
  value_px: number
  value_norm: number | null
}

export interface PredictionResult {
  image_path: string
  keypoints: [number, number][]
  keypoint_scores: number[]
  extra_pred_fields?: {
    phenotypes: Phenotype[]
  }
  overlay_path?: string
  overlay_preview_base64?: string
  overlay_thumbnail_base64?: string
  file_size?: number
}

export interface BatchResult {
  count: number
  predictions: PredictionResult[]
}

export interface ExportOptions {
  format: 'csv' | 'json' | 'images'
  output_path: string
  include_overlay: boolean
}

export interface ModelInfo {
  dataset_name: string
  num_keypoints: number
  keypoint_names: string[]
  codec_input_size: [number, number]
  phenotype_pairs: [number, number][]
  phenotype_names?: string[]
  phenotype_types?: string[]
  phenotype_scale_by_sl: boolean
  phenotype_sl_pair: [number, number] | null
}

export type AnalysisState = 'idle' | 'loading' | 'analyzing' | 'complete' | 'error'

export interface Profile {
  id: string
  name: string
  description: string
  selectedKeypoints: number[]
  selected_keypoints: number[]
  createdAt: number
  enabled: boolean
  folder_path?: string
}

export interface AppConfig {
  activeProfileId: string
  profiles: Profile[]
  darkMode: boolean
  contributionOptIn: boolean
  anonymousId: string
}
