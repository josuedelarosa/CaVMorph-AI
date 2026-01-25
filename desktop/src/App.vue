<template>
  <div id="app-container" :class="{ dark: isDarkMode }">
    <!-- Header -->
    <header class="app-header">
      <div class="header-content">
        <div class="header-title">
          <svg class="fish-logo" viewBox="0 0 24 24" width="32" height="32">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z" fill="currentColor"/>
            <circle cx="12" cy="12" r="3" fill="currentColor"/>
          </svg>
          <h1>Fish Morphometrics</h1>
        </div>
        <div class="header-actions">
          <button class="icon-btn" @click="showSettings = true" title="Profile settings">
            ⚙️
          </button>
          <button class="icon-btn" @click="toggleDarkMode" title="Toggle dark mode">
            <span v-if="isDarkMode">☀️</span>
            <span v-else>🌙</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="app-main">
      <div class="container">
        <!-- Error Banner -->
        <div v-if="errorMessage" class="error-banner">
          <span>⚠️ {{ errorMessage }}</span>
          <button class="close-btn" @click="errorMessage = ''">×</button>
        </div>

        <!-- Info Banner -->
        <div v-if="infoMessage" class="info-banner">
          <span>ℹ️ {{ infoMessage }}</span>
          <button class="close-btn" @click="infoMessage = ''">×</button>
        </div>

        <!-- Loading State -->
        <div v-if="state === 'loading' && !predictions.length" class="loading-overlay">
          <div class="spinner"></div>
          <p>Initializing backend...</p>
        </div>

        <!-- Analysis Controls -->
        <section v-if="state !== 'loading' || predictions.length" class="control-section">
          <h2>1. Select Images</h2>
          <div class="profiles-group">
            <div v-for="profile in activeProfiles" :key="profile.id" class="profile-folder-item">
              <div class="profile-header">
                <span class="profile-name">{{ profile.name }}</span>
                <span class="keypoint-badge">{{ profile.selected_keypoints.length }}/20 keypoints</span>
              </div>
              <div class="control-group">
                <button class="btn btn-primary" @click="selectFolderForProfile(profile.id)" :disabled="isAnalyzing">
                  📁 Select Folder
                </button>
                <span v-if="profile.folder_path" class="selected-path">{{ profile.folder_path }}</span>
                <span v-else class="text-muted">No folder selected</span>
                <button 
                  v-if="profile.folder_path" 
                  class="btn btn-icon"
                  @click="clearFolderForProfile(profile.id)"
                  title="Clear selection"
                >
                  ✕
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- Analysis Button -->
        <section v-if="hasActiveFoldersSelected && state !== 'analyzing'" class="control-section">
          <h2>2. Analyze</h2>
          <button 
            class="btn btn-primary" 
            @click="startAnalysis"
            :disabled="isAnalyzing"
          >
            🔬 Analyze Images
          </button>
        </section>

        <!-- Progress -->
        <div v-if="isAnalyzing" class="progress-section">
          <div class="progress-header">
            <div>
              <span>Processing: {{ processedCount }} / {{ totalCount }} images</span>
              <span class="time-est" v-if="totalCount > 0">
                ~{{ estimatedTimeRemaining }}s remaining
              </span>
            </div>
            <div class="current-file" v-if="currentProcessingFile">
              📄 {{ currentProcessingFile }}
            </div>
          </div>
          <div class="progress-bar">
            <div 
              class="progress-fill" 
              :style="{ width: progressPercent + '%' }"
            ></div>
          </div>
        </div>

        <!-- Results Section -->
        <section v-if="predictions.length" class="results-section">
          <div class="results-header">
            <div class="header-left">
              <h2>📊 Results ({{ predictions.length }} images)</h2>
              <select v-if="activeProfiles.length > 1" v-model="selectedProfileFilter" class="profile-selector">
                <option value="">All Profiles</option>
                <option v-for="profile in activeProfiles" :key="profile.id" :value="profile.id">
                  {{ profile.name }}
                </option>
              </select>
            </div>
            <div class="results-actions">
              <button class="btn btn-secondary" @click="exportResults('csv')">
                📥 Export CSV
              </button>
              <button class="btn btn-secondary" @click="exportResults('json')">
                📥 Export JSON
              </button>
              <button class="btn btn-secondary" @click="exportResults('images')">
                📥 Export Images
              </button>
              <button class="btn btn-secondary" @click="clearResults">
                🗑️ Clear
              </button>
            </div>
          </div>

          <!-- 3-Column Layout: Canvas (left) | Details (middle) | Preview List (right) -->
          <div class="results-layout-3col">
            <!-- Left Column: Canvas -->
            <div class="layout-column canvas-column">
              <div v-if="selectedPrediction" class="canvas-wrapper">
                <canvas 
                  ref="previewCanvas"
                  class="preview-canvas"
                ></canvas>
              </div>
              <div v-else class="empty-canvas">
                <p>Select an image to view</p>
              </div>
            </div>

            <!-- Middle Column: Details & Metrics -->
            <div class="layout-column details-column">
              <div v-if="selectedPrediction">
                <div class="info-header">
                  <h4>{{ getFilename(selectedPrediction.image_path) }}</h4>
                  <p class="path-text">{{ selectedPrediction.image_path }}</p>
                </div>
                
                <div class="metrics">
                  <div class="metric-card">
                    <div class="metric-label">Keypoints</div>
                    <div class="metric-value">{{ keypointCount }}/20</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Confidence</div>
                    <div class="metric-value">{{ avgConfidence }}%</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Phenotypes</div>
                    <div class="metric-value">{{ phenotypeCount }}</div>
                  </div>
                </div>
              </div>
              <div v-else class="empty-details">
                <p>Select an image</p>
              </div>
            </div>

            <!-- Right Column: Scrollable Preview List -->
            <div class="layout-column preview-list-column">
              <h4>Images</h4>
              <div class="preview-list">
                <div 
                  v-for="(pred, idx) in filteredPredictions" 
                  :key="idx"
                  class="preview-item-wrapper"
                >
                  <button 
                    class="preview-item"
                    :class="{ active: selectedPredictionIdx === idx }"
                    @click="selectPredictionFromFiltered(idx, pred)"
                    :title="getFilename(pred.image_path)"
                  >
                    <div class="preview-item-name">
                      {{ getFilename(pred.image_path) }}
                    </div>
                    <div class="preview-item-meta">
                      {{ pred.keypoints?.length || 0 }} kpts
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Phenotype Table: Full Width Below -->
          <div v-if="selectedPrediction" class="phenotype-section">
            <div class="phenotype-header">
              <h4>Measurements</h4>
            </div>
            <div class="table-compact">
              <div v-for="(value, key) in filteredPhenotypeValues" :key="key" class="table-row">
                <span class="table-key">{{ key }}</span>
                <span class="table-value">{{ value }}</span>
              </div>
            </div>
          </div>


        </section>

        <!-- Empty State -->
        <div v-if="!predictions.length && !isAnalyzing && state !== 'loading'" class="empty-state">
          <svg class="empty-icon" viewBox="0 0 100 100">
            <path d="M50 10 L60 30 L80 35 L70 50 L75 70 L55 60 L35 70 L40 50 L30 35 L50 30 Z" fill="none" stroke="currentColor" stroke-width="2"/>
          </svg>
          <h3>No results yet</h3>
          <p>Select a folder of fish images and click "Analyze" to get started</p>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="app-footer">
      <p>Fish Morphometrics v0.1.0 | Backend: <span :class="backendStatus">{{ backendStatusText }}</span></p>
    </footer>

    <!-- Settings Modal -->
    <SettingsModal
      :isOpen="showSettings"
      :profiles="profiles"
      :activeProfileId="activeProfileId"
      :keypointNames="modelInfo?.keypoint_names || []"
      @close="showSettings = false"
      @save="handleSettingsSave"
      @delete="handleDeleteProfile"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { open } from '@tauri-apps/api/dialog'
import { readBinaryFile } from '@tauri-apps/api/fs'
import type { PredictionResult, ModelInfo, AnalysisState, Profile } from './types'
import { 
  analyzeFolder, 
  getModelInfo, 
  exportCSV, 
  exportJSON, 
  exportAnnotatedImages 
} from './utils/api'
import SettingsModal from './components/SettingsModal.vue'
import {
  loadConfig,
  saveConfig,
  createProfile,
  updateProfile,
  deleteProfile,
  setActiveProfile,
  setDarkMode,
} from './utils/storage'

// State
const state = ref<AnalysisState>('loading')
const folderPath = ref('')
const predictions = ref<PredictionResult[]>([])
const selectedPredictionIdx = ref(0)
const errorMessage = ref('')
const infoMessage = ref('')
const isDarkMode = ref(false)
const isAnalyzing = ref(false)
const processedCount = ref(0)
const totalCount = ref(0)
const currentProcessingFile = ref('')
const modelInfo = ref<ModelInfo | null>(null)
const backendReady = ref(false)
const previewCanvas = ref<HTMLCanvasElement | null>(null)
const showSettings = ref(false)
const profiles = ref<Profile[]>([])
const activeProfileId = ref('default')
const selectedKeypoints = ref<Set<number>>(new Set())
const selectedProfileFilter = ref('')

// Computed
const selectedPrediction = computed(() => {
  if (!selectedProfileFilter.value) {
    return predictions.value[selectedPredictionIdx.value] || null
  }
  // When filtering by profile, get from filtered list
  return filteredPredictions.value[selectedPredictionIdx.value] || null
})

const selectedPredictionFilename = computed(() =>
  selectedPrediction.value ? getFilename(selectedPrediction.value.image_path) : ''
)

const progressPercent = computed(() => 
  totalCount.value > 0 ? (processedCount.value / totalCount.value) * 100 : 0
)

const estimatedTimeRemaining = computed(() => {
  if (totalCount.value === 0 || processedCount.value === 0) return '?'
  const avgTimePerImage = 1 // roughly 1 second per image
  const remaining = (totalCount.value - processedCount.value) * avgTimePerImage
  return Math.ceil(remaining).toString()
})

const phenotypeColumns = computed(() => {
  if (!selectedPrediction.value?.extra_pred_fields?.phenotypes) return []
  
  // Filter phenotypes to only include those where both keypoints are selected
  return selectedPrediction.value.extra_pred_fields.phenotypes
    .filter(p => {
      const [kp1, kp2] = modelInfo.value?.phenotype_pairs?.[p.id] || [p.pair[0], p.pair[1]]
      return selectedKeypoints.value.has(kp1) && selectedKeypoints.value.has(kp2)
    })
    .map(p => p.name)
})

const backendStatusText = computed(() => 
  backendReady.value ? 'Ready' : 'Connecting...'
)

const backendStatus = computed(() =>
  backendReady.value ? 'status-ready' : 'status-pending'
)

const keypointCount = computed(() => {
  if (!selectedPrediction.value) return 0
  // Get the selected profile to check which keypoints are enabled
  let selectedProfileId = selectedProfileFilter.value
  if (!selectedProfileId && selectedPrediction.value.profile_id) {
    selectedProfileId = selectedPrediction.value.profile_id
  }
  
  const activeProfile = profiles.value.find(p => p.id === selectedProfileId)
  if (activeProfile) {
    return activeProfile.selected_keypoints.length
  }
  
  // Fallback to raw count
  const scores = selectedPrediction.value.keypoint_scores || []
  if (Array.isArray(scores) && scores.length > 0 && Array.isArray(scores[0])) {
    return scores[0].length
  }
  return scores.length
})

const phenotypeCount = computed(() => {
  if (!selectedPrediction.value) return 0
  // Get the selected profile to filter phenotypes
  let selectedProfileId = selectedProfileFilter.value
  if (!selectedProfileId && selectedPrediction.value.profile_id) {
    selectedProfileId = selectedPrediction.value.profile_id
  }
  
  const activeProfile = profiles.value.find(p => p.id === selectedProfileId)
  const allPhenotypes = selectedPrediction.value.extra_pred_fields?.phenotypes || []
  
  if (activeProfile && activeProfile.phenotype_pairs) {
    // Filter phenotypes to only include those in the profile's configuration
    const pairNames = activeProfile.phenotype_pairs.map(p => p.name)
    return allPhenotypes.filter((pheno: any) => pairNames.includes(pheno.pair)).length
  }
  
  return allPhenotypes.length
})

const avgConfidence = computed(() => {
  if (!selectedPrediction.value?.keypoint_scores) return 'N/A'
  const scores = selectedPrediction.value.keypoint_scores
  let allScores: number[] = []
  
  // Handle nested arrays
  if (Array.isArray(scores) && scores.length > 0 && Array.isArray(scores[0])) {
    allScores = scores[0]
  } else if (Array.isArray(scores)) {
    allScores = scores as number[]
  }
  
  if (allScores.length === 0) return 'N/A'
  const avg = allScores.reduce((a, b) => a + b, 0) / allScores.length
  return (avg * 100).toFixed(1)
})

const selectedPhenotypeValues = computed(() => {
  if (!selectedPrediction.value) return {}
  const phenos = selectedPrediction.value.extra_pred_fields?.phenotypes || []
  const result: Record<string, string> = {}
  phenos.forEach(p => {
    const value = p.value_norm ?? p.value_px
    result[p.name] = typeof value === 'number' ? value.toFixed(2) : '-'
  })
  return result
})

const filteredPhenotypeValues = computed(() => {
  if (!selectedPrediction.value) {
    return {}
  }
  
  const profileId = selectedProfileFilter.value || activeProfiles.value[0]?.id
  if (!profileId) return {}
  
  const selectedProfile = profiles.value.find(p => p.id === profileId)
  if (!selectedProfile) return {}
  
  const phenos = selectedPrediction.value.extra_pred_fields?.phenotypes || []
  const result: Record<string, string> = {}
  
  phenos.forEach(p => {
    const [kp1, kp2] = modelInfo.value?.phenotype_pairs?.[p.id] || [p.pair[0], p.pair[1]]
    if (selectedProfile.selected_keypoints.includes(kp1) && selectedProfile.selected_keypoints.includes(kp2)) {
      const value = p.value_norm ?? p.value_px
      result[p.name] = typeof value === 'number' ? value.toFixed(2) : '-'
    }
  })
  
  return result
})

const activeProfiles = computed(() => {
  return profiles.value.filter(p => p.enabled)
})

const filteredPredictions = computed(() => {
  if (!selectedProfileFilter.value) {
    return predictions.value
  }
  return predictions.value.filter((pred: any) => pred.profile_id === selectedProfileFilter.value)
})

const hasActiveFoldersSelected = computed(() => {
  return profiles.value.some(p => p.folder_path)
})

// Methods
function getFilename(path: string): string {
  return path.split('/').pop() || path
}

function getPhenotypeValue(pred: PredictionResult, phenotypeName: string): string {
  const phenos = pred.extra_pred_fields?.phenotypes || []
  const pheno = phenos.find(p => p.name === phenotypeName)
  if (!pheno) return '-'
  const value = pheno.value_norm ?? pheno.value_px
  return typeof value === 'number' ? value.toFixed(2) : '-'
}

function selectPrediction(idx: number) {
  selectedPredictionIdx.value = idx
  drawPreview()
}

function selectPredictionFromFiltered(idx: number, pred: PredictionResult) {
  selectedPredictionIdx.value = idx
  // Auto-sync the profile filter to this prediction's profile
  if (pred.profile_id) {
    selectedProfileFilter.value = pred.profile_id
  }
  drawPreview()
}

function deselectImage(idx: number) {
  predictions.value.splice(idx, 1)
  if (selectedPredictionIdx.value >= predictions.value.length) {
    selectedPredictionIdx.value = Math.max(0, predictions.value.length - 1)
  }
  if (predictions.value.length > 0) {
    drawPreview()
  } else {
    selectedPredictionIdx.value = -1
  }
}


async function selectFolderForProfile(profileId: string) {
  try {
    const selected = await open({
      directory: true,
      multiple: false,
    })
    if (selected && typeof selected === 'string') {
      const profileIdx = profiles.value.findIndex(p => p.id === profileId)
      if (profileIdx !== -1) {
        profiles.value[profileIdx].folder_path = selected
        await saveConfig({
          dark_mode: isDarkMode.value,
          active_profile: activeProfileId.value,
          profiles: profiles.value,
        })
        infoMessage.value = `Folder set for ${profiles.value[profileIdx].name}`
      }
    }
  } catch (err) {
    errorMessage.value = `Failed to select folder: ${err}`
  }
}

async function clearFolderForProfile(profileId: string) {
  const profileIdx = profiles.value.findIndex(p => p.id === profileId)
  if (profileIdx !== -1) {
    profiles.value[profileIdx].folder_path = ''
    await saveConfig({
      dark_mode: isDarkMode.value,
      active_profile: activeProfileId.value,
      profiles: profiles.value,
    })
    infoMessage.value = `Folder cleared for ${profiles.value[profileIdx].name}`
  }
}

async function startAnalysis() {
  const activeFolders = profiles.value.filter(p => p.folder_path)
  if (activeFolders.length === 0) {
    errorMessage.value = 'Please select at least one folder for a profile'
    return
  }

  try {
    isAnalyzing.value = true
    state.value = 'analyzing'
    predictions.value = []
    processedCount.value = 0
    totalCount.value = 0
    currentProcessingFile.value = 'Loading model...'
    errorMessage.value = ''
    infoMessage.value = 'Starting analysis...'

    // Analyze each active profile's folder
    const allPredictions: Array<PredictionResult & { profile_id: string }> = []
    let totalProcessed = 0

    for (const profile of activeFolders) {
      const result = await analyzeFolder(
        profile.folder_path,
        true,
        undefined,
        profile.id,
        profile.name
      )
      const withProfile = result.predictions.map(pred => ({
        ...pred,
        profile_id: profile.id,
      }))
      allPredictions.push(...withProfile)
      totalProcessed += result.count
    }

    predictions.value = allPredictions as PredictionResult[]
    processedCount.value = totalProcessed
    totalCount.value = totalProcessed
    currentProcessingFile.value = ''

    // Initialize profile filter to first active profile if not set
    if (selectedProfileFilter.value === '' && activeProfiles.value.length > 0) {
      selectedProfileFilter.value = activeProfiles.value[0].id
    }

    state.value = 'complete'
    infoMessage.value = `Analysis complete! Processed ${totalProcessed} images.`

    if (predictions.value.length > 0) {
      selectPrediction(0)
    }
  } catch (err) {
    state.value = 'error'
    errorMessage.value = `Analysis failed: ${err}`
    currentProcessingFile.value = ''
  } finally {
    isAnalyzing.value = false
  }
}

async function exportResults(format: 'csv' | 'json' | 'images') {
  if (predictions.value.length === 0) {
    errorMessage.value = 'No results to export'
    return
  }

  try {
    const timestamp = new Date().toISOString().slice(0, 10)
    
    // Group predictions by profile
    const predictionsByProfile = new Map<string, PredictionResult[]>()
    for (const pred of predictions.value) {
      const profileId = (pred as any).profile_id || 'default'
      if (!predictionsByProfile.has(profileId)) {
        predictionsByProfile.set(profileId, [])
      }
      predictionsByProfile.get(profileId)!.push(pred)
    }

    // Export for each active profile
    for (const [profileId, profilePreds] of predictionsByProfile.entries()) {
      const profile = profiles.value.find(p => p.id === profileId)
      if (!profile) continue

      let outputPath = ''

      if (format === 'images') {
        const baseDir = await open({
          directory: true,
          defaultPath: profile.folder_path,
        })
        if (!baseDir || typeof baseDir !== 'string') continue
        outputPath = `${baseDir}/results_${profile.name}_${timestamp}`
      } else {
        const filename = `${profile.name}_results_${timestamp}`
        outputPath = `/tmp/${filename}.${format}`
      }

      if (format === 'csv') {
        await exportCSV(outputPath, profilePreds)
      } else if (format === 'json') {
        await exportJSON(outputPath, profilePreds)
      } else if (format === 'images') {
        await exportAnnotatedImages(outputPath, profilePreds)
      }

      infoMessage.value = `Exported ${profile.name} results to ${outputPath}`
    }
  } catch (err) {
    errorMessage.value = `Export failed: ${err}`
  }
}

function clearResults() {
  if (confirm('Clear all results? This cannot be undone.')) {
    predictions.value = []
    folderPath.value = ''
    state.value = 'idle'
  }
}

function drawPreview() {
  if (!previewCanvas.value || !selectedPrediction.value) return

  const canvas = previewCanvas.value
  const pred = selectedPrediction.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // Get canvas dimensions from DOM
  const rect = canvas.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  
  canvas.width = (rect.width || 600) * dpr
  canvas.height = (rect.height || 350) * dpr
  
  ctx.scale(dpr, dpr)

  // Try to load and draw image from file path
  const imagePath = pred.image_path
  console.log('drawCanvas - imagePath:', imagePath)
  
  if (imagePath) {
    const img = new Image()
    
    // Read file using Tauri API and convert to data URL
    readBinaryFile(imagePath)
      .then((data) => {
        // Determine MIME type based on file extension
        const ext = imagePath.toLowerCase().split('.').pop()
        const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg'
        
        // Create blob and data URL
        const blob = new Blob([data], { type: mimeType })
        const dataUrl = URL.createObjectURL(blob)
        console.log('Created data URL for image')
        
        img.src = dataUrl
      })
      .catch((err) => {
        console.error('Failed to read file:', err)
        // Fallback: draw keypoints on gray background
        ctx.fillStyle = '#f0f0f0'
        ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr)
        drawKeypointsOnCanvas(ctx, pred, canvas, null, 1, 0, 0, dpr)
      })
    
    img.onload = () => {
      console.log('Image loaded successfully:', imagePath)
      
      const displayWidth = canvas.width / dpr
      const displayHeight = canvas.height / dpr
      
      // Calculate scale to fit image in canvas while maintaining aspect ratio
      const imgAspect = img.width / img.height
      const canvasAspect = displayWidth / displayHeight
      
      let drawWidth = displayWidth
      let drawHeight = displayHeight
      let offsetX = 0
      let offsetY = 0
      
      if (imgAspect > canvasAspect) {
        // Image wider than canvas - fit to width
        drawWidth = displayWidth
        drawHeight = displayWidth / imgAspect
        offsetY = (displayHeight - drawHeight) / 2
      } else {
        // Image taller than canvas - fit to height
        drawHeight = displayHeight
        drawWidth = displayHeight * imgAspect
        offsetX = (displayWidth - drawWidth) / 2
      }
      
      // Draw gray background first
      ctx.fillStyle = '#f0f0f0'
      ctx.fillRect(0, 0, displayWidth, displayHeight)
      
      // Draw image centered
      ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight)
      
      // Draw keypoints with correct scale
      const scale = drawWidth / img.width
      drawKeypointsOnCanvas(ctx, pred, canvas, img, scale, offsetX, offsetY, dpr)
    }
    
    img.onerror = (e) => {
      console.error('Failed to load image:', imagePath, e)
      console.log('Falling back to keypoints only on gray background')
      // If image fails to load, just draw keypoints on gray background
      ctx.fillStyle = '#f0f0f0'
      ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr)
      drawKeypointsOnCanvas(ctx, pred, canvas, null, 1, 0, 0, dpr)
    }
  } else {
    console.warn('No image path provided')
    // No image path, just draw keypoints
    ctx.fillStyle = '#f0f0f0'
    ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr)
    drawKeypointsOnCanvas(ctx, pred, canvas, null, 1, 0, 0, dpr)
  }
}

function drawKeypointsOnCanvas(
  ctx: CanvasRenderingContext2D,
  pred: PredictionResult,
  canvas: HTMLCanvasElement,
  img: HTMLImageElement | null,
  scale: number,
  offsetX: number,
  offsetY: number,
  dpr: number = 1
) {
  let keypoints = pred.keypoints || []
  let scores = pred.keypoint_scores || []

  // Flatten nested arrays if needed
  // [[[x,y],...]] -> [[x,y],...]
  if (Array.isArray(keypoints) && keypoints.length > 0) {
    if (Array.isArray(keypoints[0]) && Array.isArray(keypoints[0][0])) {
      keypoints = keypoints[0]
    }
  }

  // [[score1, score2, ...]] -> [score1, score2, ...]
  if (Array.isArray(scores) && scores.length > 0) {
    if (Array.isArray(scores[0])) {
      scores = scores[0]
    }
  }

  // Get selected keypoints for the currently displayed profile
  let profileId = selectedProfileFilter.value
  if (!profileId && selectedPrediction.value?.profile_id) {
    profileId = selectedPrediction.value.profile_id
  }
  const displayProfile = profiles.value.find(p => p.id === profileId)
  const displayKeypoints = displayProfile?.selected_keypoints ? new Set(displayProfile.selected_keypoints) : selectedKeypoints.value

  const maxPoints = Math.min(keypoints.length, scores.length)
  
  for (let i = 0; i < maxPoints; i++) {
    // Only draw keypoints that are in the displayed profile
    if (!displayKeypoints.has(i)) continue

    const kpt = keypoints[i]
    const score = scores[i] || 0
    
    if (!Array.isArray(kpt) || kpt.length < 2) continue
    
    const x = Number(kpt[0])
    const y = Number(kpt[1])
    
    if (isNaN(x) || isNaN(y)) continue
    
    // Scale to canvas
    const px = offsetX + (x * scale)
    const py = offsetY + (y * scale)

    // Draw circle
    ctx.fillStyle = score > 0.5 ? '#00ff00' : '#ffff00'
    ctx.strokeStyle = '#000000'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.arc(px, py, 4, 0, Math.PI * 2)
    ctx.fill()
    ctx.stroke()

    // Draw label
    ctx.fillStyle = '#000000'
    ctx.font = 'bold 10px sans-serif'
    ctx.fillText(`${i + 1}`, px + 6, py + 4)
  }

  // Draw confidence info
  if (scores.length > 0) {
    ctx.fillStyle = '#000000'
    ctx.font = 'bold 12px sans-serif'
    const avgScore = scores.reduce((a, b) => a + (Number(b) || 0), 0) / scores.length
    const confText = isNaN(avgScore) ? 'N/A' : `${(avgScore * 100).toFixed(1)}%`
    ctx.fillText(`Avg Confidence: ${confText}`, 10, (canvas.height / dpr) - 10)
  }
}

async function initializeBackend() {
  try {
    // Try to load model info
    modelInfo.value = await getModelInfo()
    backendReady.value = true
    state.value = 'idle'
    errorMessage.value = ''
  } catch (err) {
    // Don't retry forever - just show error once and continue
    console.error('Failed to load model info:', err)
    errorMessage.value = `Backend connection error: ${err}`
    // Still mark as loaded so UI is visible
    state.value = 'idle'
    backendReady.value = false
    // Try again after 5 seconds
    setTimeout(() => {
      initializeBackend()
    }, 5000)
  }
}

function toggleDarkMode() {
  isDarkMode.value = !isDarkMode.value
  setDarkMode(isDarkMode.value)
}

async function handleSettingsSave(data: {
  activeProfileId: string
  selectedKeypoints: number[]
  newProfile?: { name: string; description: string }
}) {
  try {
    // Create new profile if requested
    if (data.newProfile) {
      const newProf = await createProfile(
        data.newProfile.name,
        data.newProfile.description,
        data.selectedKeypoints
      )
      activeProfileId.value = newProf.id
      profiles.value.push(newProf)
      infoMessage.value = `Created profile: ${newProf.name}`
    } else {
      // Update active profile
      await setActiveProfile(data.activeProfileId)
      const profile = profiles.value.find(p => p.id === data.activeProfileId)
      if (profile) {
        await updateProfile(data.activeProfileId, {
          selectedKeypoints: data.selectedKeypoints
        })
        profile.selectedKeypoints = data.selectedKeypoints
        activeProfileId.value = data.activeProfileId
        infoMessage.value = `Profile updated`
      }
    }

    // Update selected keypoints for drawing
    selectedKeypoints.value = new Set(data.selectedKeypoints)
    showSettings.value = false
    drawPreview()
  } catch (err) {
    errorMessage.value = `Failed to save settings: ${err}`
  }
}

async function handleDeleteProfile(profileId: string) {
  try {
    await deleteProfile(profileId)
    profiles.value = profiles.value.filter(p => p.id !== profileId)
    
    // If deleted profile was active, switch to default
    if (activeProfileId.value === profileId) {
      activeProfileId.value = 'default'
      await setActiveProfile('default')
    }
    
    infoMessage.value = 'Profile deleted'
  } catch (err) {
    errorMessage.value = `Failed to delete profile: ${err}`
  }
}

onMounted(async () => {
  // Load config
  try {
    const config = await loadConfig()
    isDarkMode.value = config.darkMode
    profiles.value = config.profiles.map(p => ({
      ...p,
      selected_keypoints: p.selected_keypoints || p.selectedKeypoints || [],
      enabled: p.enabled !== undefined ? p.enabled : true,
    }))
    activeProfileId.value = config.activeProfileId
    
    // Initialize profile filter to first active profile
    const activeProfiles = profiles.value.filter(p => p.enabled)
    if (activeProfiles.length > 0) {
      selectedProfileFilter.value = activeProfiles[0].id
    }

    // Load active profile's keypoints
    const activeProfile = profiles.value.find(p => p.id === config.activeProfileId)
    if (activeProfile) {
      selectedKeypoints.value = new Set(activeProfile.selected_keypoints || activeProfile.selectedKeypoints)
    }
  } catch (err) {
    console.error('Failed to load config:', err)
  }

  // Initialize backend immediately but don't block UI
  initializeBackend()
  // Set state to idle after 1 second anyway so UI shows
  setTimeout(() => {
    if (state.value === 'loading') {
      state.value = 'idle'
    }
  }, 1000)
})

watch(() => selectedPredictionIdx.value, async () => {
  await nextTick()
  drawPreview()
})

// Reset selection when filtering by profile
watch(() => selectedProfileFilter.value, () => {
  selectedPredictionIdx.value = 0
})

// Auto-draw preview when predictions become available
watch(() => filteredPredictions.value.length, async () => {
  if (filteredPredictions.value.length > 0) {
    await nextTick()
    drawPreview()
  }
})
</script>

<style scoped>
/* CSS will be in main.css */
</style>
