<template>
  <!-- First Run Setup View -->
  <SetupView 
    v-if="needsSetup" 
    @setup-complete="onSetupComplete"
    @setup-error="onSetupError"
  />
  
  <!-- Main App (shown after setup is complete) -->
  <div v-else id="app-container" :class="{ dark: isDarkMode }">
    <!-- Header -->
    <header class="app-header">
      <div class="header-content">
        <div class="header-title">
          <svg class="fish-logo" viewBox="0 0 24 24" width="32" height="32">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z" fill="currentColor"/>
            <circle cx="12" cy="12" r="3" fill="currentColor"/>
          </svg>
          <h1>PhenoAI</h1>
        </div>
        <div class="header-actions">
          <button class="icon-btn" @click="showDebugConsole = !showDebugConsole" title="Toggle Debug Console">
            {{ showDebugConsole ? '📋' : '🔍' }}
          </button>
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

    <!-- Debug Console -->
    <div v-if="showDebugConsole" class="debug-console">
      <div class="debug-header">
        <strong>🔍 Debug Console</strong>
        <div>
          <button @click="debugLogs = []" class="btn-sm">Clear</button>
          <button @click="showDebugConsole = false" class="btn-sm">Close</button>
        </div>
      </div>
      <div class="debug-content">
        <div v-for="(log, idx) in debugLogs.slice(-100)" :key="idx" class="debug-log" :class="log.level">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        <div v-if="debugLogs.length === 0" class="debug-empty">No logs yet</div>
      </div>
    </div>

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
          
          <!-- Show warning if no active profiles -->
          <div v-if="activeProfiles.length === 0" class="warning-message">
            <p>⚠️ No active profiles configured. Go to Settings (⚙️) to create or enable a profile.</p>
          </div>
          
          <div v-else class="profiles-group">
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
          <div class="results-layout-2col" :class="{ 'focus-mode': focusMode }">
            <!-- Main: Large Preview -->
            <div class="main-preview">
              <div class="preview-header">
                <div class="preview-title" v-if="selectedPrediction">
                  {{ getFilename(selectedPrediction.image_path) }}
                </div>
                <button class="btn-icon" @click="focusMode = !focusMode" :title="focusMode ? 'Show sidebar' : 'Focus mode'">
                  {{ focusMode ? '⬅️' : '⬆️' }}
                </button>
              </div>
              <div v-if="selectedPrediction" class="canvas-container">
                <canvas 
                  ref="previewCanvas"
                  class="preview-canvas"
                ></canvas>
              </div>
              <div v-else class="empty-canvas">
                <p>Select an image to view</p>
              </div>
              <div class="preview-footer" v-if="selectedPrediction">
                <div class="metric-inline">
                  <span class="metric-label">Keypoints:</span>
                  <span class="metric-value">{{ keypointCount }}/20</span>
                </div>
                <div class="metric-inline">
                  <span class="metric-label">Confidence:</span>
                  <span class="metric-value">{{ avgConfidence }}%</span>
                </div>
                <div class="metric-inline">
                  <span class="metric-label">Phenotypes:</span>
                  <span class="metric-value">{{ phenotypeCount }}</span>
                </div>
              </div>
            </div>

            <!-- Sidebar: Image List -->
            <div class="sidebar" v-if="!focusMode">
              <div class="sidebar-header">
                <h4>Images ({{ filteredPredictions.length }})</h4>
              </div>
              <div class="image-grid">
                <button 
                  v-for="(pred, idx) in filteredPredictions" 
                  :key="idx"
                  class="image-thumb"
                  :class="{ active: selectedPredictionIdx === idx }"
                  @click="selectPredictionFromFiltered(idx, pred)"
                  :title="getFilename(pred.image_path)"
                >
                  <div class="thumb-placeholder">
                    <!-- Use overlay_png_base64 for instant loading (shows all keypoints but loads fast) -->
                    <img 
                      v-if="pred.overlay_png_base64"
                      :src="'data:image/png;base64,' + pred.overlay_png_base64"
                      alt="Thumbnail"
                      class="thumb-image"
                      @error="(e) => (e.target as HTMLImageElement).style.display = 'none'"
                    />
                    <span v-else class="thumb-number">{{ idx + 1 }}</span>
                  </div>
                  <div class="thumb-info">
                    <div class="thumb-name">{{ getFilename(pred.image_path).substring(0, 20) }}{{ getFilename(pred.image_path).length > 20 ? '...' : '' }}</div>
                    <div class="thumb-meta">
                      {{ getKeypointCount(pred) }}/20 • {{ getAvgConfidence(pred) }}% • {{ getPhenotypeCount(pred) }}p
                    </div>
                  </div>
                </button>
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

    <!-- Debug Console -->
    <div v-if="showDebugConsole" class="debug-console">
      <div class="debug-header">
        <strong>Debug Console</strong>
        <button @click="debugLogs = []" class="btn-sm">Clear</button>
        <button @click="showDebugConsole = false" class="btn-sm">Close</button>
      </div>
      <div class="debug-content">
        <div v-for="(log, idx) in debugLogs.slice(-100)" :key="idx" class="debug-log" :class="log.level">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <footer class="app-footer">
      <p>PhenoAI v0.1.0 | Backend: <span :class="backendStatus">{{ backendStatusText }}</span></p>
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
    
    <!-- Welcome Guide -->
    <WelcomeGuide
      :show="showWelcome"
      @close="showWelcome = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { invoke, convertFileSrc } from '@tauri-apps/api/tauri'
import { open } from '@tauri-apps/api/dialog'
import { readBinaryFile } from '@tauri-apps/api/fs'
import { homeDir } from '@tauri-apps/api/path'
import type { PredictionResult, ModelInfo, AnalysisState, Profile } from './types'
import { 
  analyzeFolder, 
  getModelInfo, 
  exportCSV, 
  exportJSON, 
  exportAnnotatedImages 
} from './utils/api'
import SettingsModal from './components/SettingsModal.vue'
import SetupView from './views/SetupView.vue'
import WelcomeGuide from './components/WelcomeGuide.vue'
import {
  loadConfig,
  saveConfig,
  createProfile,
  updateProfile,
  deleteProfile,
  setActiveProfile,
  setDarkMode,
} from './utils/storage'

// Setup State
const needsSetup = ref(true)  // Default to showing setup, will be checked on mount

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
const showDebugConsole = ref(false)
const debugLogs = ref<Array<{time: string, level: string, message: string}>>([])
const profiles = ref<Profile[]>([])
const activeProfileId = ref('default')
const selectedKeypoints = ref<Set<number>>(new Set())
const selectedProfileFilter = ref('')
const showWelcome = ref(false)

// Intercept console.log/error/warn for debug panel
const originalLog = console.log
const originalError = console.error
const originalWarn = console.warn

console.log = (...args: any[]) => {
  debugLogs.value.push({ time: new Date().toLocaleTimeString(), level: 'log', message: args.join(' ') })
  originalLog(...args)
}
console.error = (...args: any[]) => {
  debugLogs.value.push({ time: new Date().toLocaleTimeString(), level: 'error', message: args.join(' ') })
  originalError(...args)
}
console.warn = (...args: any[]) => {
  debugLogs.value.push({ time: new Date().toLocaleTimeString(), level: 'warn', message: args.join(' ') })
  originalWarn(...args)
}

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

const focusMode = ref(false)

// Helper function to get keypoint count for any prediction
function getKeypointCount(pred: PredictionResult): number {
  const scores = pred.keypoint_scores || []
  if (Array.isArray(scores) && scores.length > 0 && Array.isArray(scores[0])) {
    return scores[0].length
  }
  return scores.length
}

// Helper function to get average confidence for any prediction
function getAvgConfidence(pred: PredictionResult): string {
  const scores = pred.keypoint_scores || []
  let allScores: number[] = []
  
  if (Array.isArray(scores) && scores.length > 0 && Array.isArray(scores[0])) {
    allScores = scores[0]
  } else if (Array.isArray(scores)) {
    allScores = scores as number[]
  }
  
  if (allScores.length === 0) return 'N/A'
  const avg = allScores.reduce((a, b) => a + b, 0) / allScores.length
  return (avg * 100).toFixed(0)
}

// Helper function to get phenotype count for any prediction
function getPhenotypeCount(pred: PredictionResult): number {
  return pred.extra_pred_fields?.phenotypes?.length || 0
}

const keypointCount = computed(() => {
  if (!selectedPrediction.value) return 0
  return getKeypointCount(selectedPrediction.value)
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
    console.log('[Filtered] No filter, returning', predictions.value.length, 'predictions')
    if (predictions.value.length > 0) {
      console.log('[Filtered] First pred has overlay_png_base64:', !!predictions.value[0].overlay_png_base64, 'length:', predictions.value[0].overlay_png_base64?.length)
      console.log('[Filtered] First pred image_path:', predictions.value[0].image_path)
    }
    return predictions.value
  }
  const filtered = predictions.value.filter((pred: any) => pred.profile_id === selectedProfileFilter.value)
  console.log('[Filtered] Profile filter applied:', selectedProfileFilter.value, 'returned', filtered.length, 'predictions')
  if (filtered.length > 0) {
    console.log('[Filtered] First filtered pred has overlay_png_base64:', !!filtered[0].overlay_png_base64)
  }
  return filtered
})

const hasActiveFoldersSelected = computed(() => {
  return profiles.value.some(p => p.folder_path)
})

// Methods
function getFilename(path: string): string {
  return path.split('/').pop() || path
}

function getImageDataUrl(imagePath: string): string {
  // Convert file path to Tauri asset protocol URL for secure loading
  if (!imagePath) return ''
  return convertFileSrc(imagePath)
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
  // Keep current profile filter selection (don't auto-switch)
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
      
      // Log first prediction to check if overlay_png_base64 is present
      if (withProfile.length > 0) {
        const first = withProfile[0]
        console.log('📦 First prediction data:', {
          image_path: first.image_path,
          has_overlay_base64: !!first.overlay_png_base64,
          overlay_length: first.overlay_png_base64?.length || 0,
          overlay_preview: first.overlay_png_base64 ? first.overlay_png_base64.substring(0, 50) + '...' : 'none',
          has_keypoints: !!first.keypoints,
          keypoint_count: first.keypoints?.length || 0
        })
        
        // TEST: Try to create an image immediately to verify data
        if (first.overlay_png_base64) {
          const testImg = new Image()
          testImg.onload = () => console.log('✅ TEST: Base64 image loads OK:', testImg.width, 'x', testImg.height)
          testImg.onerror = (e) => console.error('❌ TEST: Base64 image failed to load:', e)
          testImg.src = 'data:image/jpeg;base64,' + first.overlay_png_base64
        }
      }
      
      allPredictions.push(...withProfile)
      totalProcessed += result.count
    }

    predictions.value = allPredictions as PredictionResult[]
    processedCount.value = totalProcessed
    totalCount.value = totalProcessed
    currentProcessingFile.value = ''

    // Keep profile filter as ALL PROFILES (empty string) by default
    // User can manually select a specific profile if needed

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

// Filter predictions based on profile's selected keypoints
function filterPredictionsByProfile(pred: PredictionResult, profile: Profile): PredictionResult {
  const selectedKpts = new Set(profile.selected_keypoints)
  
  console.log('[Filter Pred] Profile selected keypoints:', Array.from(selectedKpts))
  
  // Get keypoints and scores
  let kpts = pred.keypoints || []
  let scores = pred.keypoint_scores || []
  
  console.log('[Filter Pred] Original keypoints count:', kpts.length)
  
  // Flatten nested arrays if needed
  if (Array.isArray(kpts) && kpts.length > 0 && Array.isArray(kpts[0]) && Array.isArray(kpts[0][0])) {
    kpts = kpts[0]
  }
  if (Array.isArray(scores) && scores.length > 0 && Array.isArray(scores[0])) {
    scores = scores[0]
  }
  
  // Filter keypoints and scores to only selected ones
  // IMPORTANT: Store keypoints in dict format with original IDs preserved
  const filteredKpts: any[] = []
  const filteredScores: any[] = []
  const keypointIds: number[] = []  // Track original indices
  
  for (let i = 0; i < kpts.length; i++) {
    if (selectedKpts.has(i)) {
      // Store as dict with name to preserve original keypoint ID
      filteredKpts.push({
        x: kpts[i][0],
        y: kpts[i][1],
        name: `${i + 1}`,  // Original keypoint number (1-indexed for display)
        score: i < scores.length ? scores[i] : 1.0
      })
      keypointIds.push(i)
    }
  }
  
  console.log('[Filter Pred] Filtered keypoints count:', filteredKpts.length)
  console.log('[Filter Pred] Keypoint IDs preserved:', keypointIds)
  
  // Filter phenotypes - only include if both keypoints are selected
  const phenotypes = pred.extra_pred_fields?.phenotypes || []
  const filteredPhenotypes = phenotypes.filter(p => {
    const [kp1, kp2] = modelInfo.value?.phenotype_pairs?.[p.id] || [p.pair[0], p.pair[1]]
    return selectedKpts.has(kp1) && selectedKpts.has(kp2)
  })
  
  console.log('[Filter Pred] Original phenotypes:', phenotypes.length, 'Filtered:', filteredPhenotypes.length)
  
  // Return filtered prediction with dict-format keypoints (preserves IDs)
  return {
    ...pred,
    keypoints: filteredKpts,  // Now in dict format: [{x, y, name, score}, ...]
    // Don't include keypoint_scores separately since they're in the dicts
    extra_pred_fields: {
      ...pred.extra_pred_fields,
      phenotypes: filteredPhenotypes
    }
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

      console.log('[Export] Profile:', profile.name)
      console.log('[Export] Profile selected_keypoints:', profile.selected_keypoints)
      console.log('[Export] Before filtering - predictions count:', profilePreds.length)
      console.log('[Export] Before filtering - sample keypoints:', profilePreds[0]?.keypoints?.length)

      // Filter predictions to only include selected keypoints and phenotypes
      const filteredPreds = profilePreds.map(pred => filterPredictionsByProfile(pred, profile))

      console.log('[Export] After filtering - predictions count:', filteredPreds.length)
      console.log('[Export] After filtering - sample keypoints:', filteredPreds[0]?.keypoints?.length)
      console.log('[Export] After filtering - sample phenotypes:', filteredPreds[0]?.extra_pred_fields?.phenotypes?.length)

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
        const documentsDir = await homeDir()
        const exportDir = `${documentsDir}/Documents/PhenoAI`
        // Create directory if it doesn't exist (handled by backend)
        outputPath = `${exportDir}/${filename}.${format}`
      }

      if (format === 'csv') {
        await exportCSV(outputPath, filteredPreds)
      } else if (format === 'json') {
        await exportJSON(outputPath, filteredPreds)
      } else if (format === 'images') {
        await exportAnnotatedImages(outputPath, filteredPreds)
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

  // Get canvas container dimensions
  const rect = canvas.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  
  // Use container size for display
  const displayWidth = Math.max(rect.width || 800, 800)
  const displayHeight = Math.max(rect.height || 600, 600)
  
  canvas.width = displayWidth * dpr
  canvas.height = displayHeight * dpr
  canvas.style.width = displayWidth + 'px'
  canvas.style.height = displayHeight + 'px'
  
  ctx.scale(dpr, dpr)

  // Prefer overlay_png_base64 from backend if available
  console.log('🖼️ drawPreview called:', {
    has_overlay_base64: !!pred.overlay_png_base64,
    overlay_length: pred.overlay_png_base64?.length || 0,
    image_path: pred.image_path
  })
  
  // IMPORTANT: Do NOT use overlay_png_base64 because it has ALL keypoints pre-rendered
  // Instead, always load the raw image and draw filtered keypoints on top
  console.log('📂 Loading RAW image to draw filtered keypoints')
  
  // Fallback: Try to load and draw image from file path
  function loadImageFromPath() {
    console.log('⚠️ No overlay_png_base64, falling back to file path loading')
    const imagePath = pred.image_path
    console.log('📂 Loading from path:', imagePath)

    if (imagePath) {
      const img = new Image()

      // Read file using Tauri API and convert to data URL
      readBinaryFile(imagePath)
        .then((data) => {
          const ext = imagePath.toLowerCase().split('.').pop()
          const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg'
          const blob = new Blob([data], { type: mimeType })
          const dataUrl = URL.createObjectURL(blob)
          console.log('Created data URL for image')
          img.src = dataUrl
        })
        .catch((err) => {
          console.error('Failed to read file:', err)
          ctx.fillStyle = '#f0f0f0'
          ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr)
          drawKeypointsOnCanvas(ctx, pred, canvas, null, 1, 0, 0, dpr)
        })

      img.onload = () => {
        console.log('Image loaded successfully from file:', imagePath)
        const displayWidth = canvas.width / dpr
        const displayHeight = canvas.height / dpr

        const scale = Math.min(displayWidth / img.width, displayHeight / img.height)
        const scaledWidth = img.width * scale
        const scaledHeight = img.height * scale
        const offsetX = (displayWidth - scaledWidth) / 2
        const offsetY = (displayHeight - scaledHeight) / 2

        ctx.fillStyle = '#f0f0f0'
        ctx.fillRect(0, 0, displayWidth, displayHeight)
        ctx.drawImage(img, offsetX, offsetY, scaledWidth, scaledHeight)
        drawKeypointsOnCanvas(ctx, pred, canvas, img, scale, offsetX, offsetY, dpr)
      }

      img.onerror = (e) => {
        console.error('Failed to load image:', imagePath, e)
        console.log('Falling back to keypoints only on gray background')
        ctx.fillStyle = '#f0f0f0'
        ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr)
        drawKeypointsOnCanvas(ctx, pred, canvas, null, 1, 0, 0, dpr)
      }
    } else {
      console.warn('No image path provided')
      ctx.fillStyle = '#f0f0f0'
      ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr)
      drawKeypointsOnCanvas(ctx, pred, canvas, null, 1, 0, 0, dpr)
    }
  }

  loadImageFromPath()
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

  // Debug logging
  console.log('[Canvas Draw] Profile ID:', profileId)
  console.log('[Canvas Draw] Display Profile:', displayProfile)
  console.log('[Canvas Draw] Selected Keypoints:', displayProfile?.selected_keypoints || Array.from(selectedKeypoints.value))
  console.log('[Canvas Draw] Display Keypoints Set:', Array.from(displayKeypoints))
  console.log('[Canvas Draw] Total keypoints to check:', keypoints.length)

  const maxPoints = Math.min(keypoints.length, scores.length)
  let drawnCount = 0
  
  for (let i = 0; i < maxPoints; i++) {
    // Only draw keypoints that are in the displayed profile
    if (!displayKeypoints.has(i)) continue
    drawnCount++

    const kpt = keypoints[i]
    const score = scores[i] || 0
    
    if (!Array.isArray(kpt) || kpt.length < 2) continue
    
    const x = Number(kpt[0])
    const y = Number(kpt[1])
    
    if (isNaN(x) || isNaN(y)) continue
    
    // Scale to canvas
    const px = offsetX + (x * scale)
    const py = offsetY + (y * scale)

    // Calculate normalized keypoint size based on canvas dimensions
    const canvasAvg = (canvas.width + canvas.height) / (2 * dpr)
    const baseSize = Math.max(3, Math.min(10, canvasAvg / 100))
    
    // Debug logging for first keypoint
    if (i === 0) {
      console.log(`[Keypoint Debug] Canvas: ${canvas.width}x${canvas.height}, DPR: ${dpr}, Avg: ${canvasAvg}, BaseSize: ${baseSize}, Score: ${score}`)
    }
    
    // Use pure red color to match exported images
    const color = 'rgb(255, 0, 0)'  // Pure red, same as backend
    
    // Draw solid red keypoint circle (no border, no white center)
    ctx.shadowColor = color
    ctx.shadowBlur = baseSize * 1.5
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(px, py, baseSize, 0, Math.PI * 2)
    ctx.fill()
    
    // Draw keypoint number with outline for readability
    ctx.shadowBlur = 0
    ctx.fillStyle = 'white'
    ctx.strokeStyle = 'black'
    ctx.lineWidth = Math.max(2, baseSize * 0.3)
    ctx.font = `bold ${Math.max(10, baseSize * 1.8)}px sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.strokeText(`${i + 1}`, px, py - baseSize * 2.2)
    ctx.fillText(`${i + 1}`, px, py - baseSize * 2.2)
    
    // Reset shadow
    ctx.shadowBlur = 0
  }

  console.log('[Canvas Draw] Drew', drawnCount, 'out of', maxPoints, 'keypoints')

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
  const maxRetries = 12  // 12 * 2s = 24 seconds max wait
  let retries = 0
  
  const attemptConnection = async () => {
    try {
      // Show status in UI
      if (retries > 0) {
        errorMessage.value = `Connecting to backend... (attempt ${retries}/${maxRetries})`
      }
      
      // Try to load model info
      modelInfo.value = await getModelInfo()
      backendReady.value = true
      state.value = 'idle'
      errorMessage.value = ''
      console.log('✓ Backend connected successfully')
    } catch (err) {
      retries++
      
      // Extract detailed error information
      let errorDetails = 'Unknown error'
      if (err instanceof Error) {
        errorDetails = `${err.name}: ${err.message}`
        console.error(`[${retries}/${maxRetries}] Error details:`, {
          name: err.name,
          message: err.message,
          stack: err.stack
        })
      }
      
      console.log(`Backend connection attempt ${retries}/${maxRetries} failed:`, errorDetails)
      
      if (retries < maxRetries) {
        // Still waiting for backend to start - retry in 2 seconds
        errorMessage.value = `Connecting... (${retries}/${maxRetries}) ${errorDetails}`
        setTimeout(attemptConnection, 2000)
      } else {
        // Max retries reached - show error
        console.error('Failed to connect to backend after max retries:', err)
        errorMessage.value = `⚠️ Backend connection error: ${errorDetails}`
        state.value = 'idle'
        backendReady.value = false
        // Try one more time after 10 seconds in case backend is slow
        setTimeout(attemptConnection, 10000)
      }
    }
  }
  
  // Start trying
  attemptConnection()
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
      selectedProfileFilter.value = newProf.id
      selectedKeypoints.value = new Set(data.selectedKeypoints)
      infoMessage.value = `Created profile: ${newProf.name}`
    } else {
      // Update active profile
      await setActiveProfile(data.activeProfileId)
      const profile = profiles.value.find(p => p.id === data.activeProfileId)
      if (profile) {
        await updateProfile(data.activeProfileId, {
          selectedKeypoints: data.selectedKeypoints,
          selected_keypoints: data.selectedKeypoints
        })
        profile.selectedKeypoints = data.selectedKeypoints
        profile.selected_keypoints = data.selectedKeypoints
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

// Setup handlers
async function checkIfSetupNeeded(): Promise<boolean> {
  try {
    return await invoke<boolean>('check_setup_needed')
  } catch (err) {
    console.error('Failed to check setup status:', err)
    // Assume setup is NOT needed if we can't check (dev mode)
    return false
  }
}

async function onSetupComplete() {
  needsSetup.value = false
  
  // Show welcome guide for first-time users
  const welcomeShown = localStorage.getItem('phenoai-welcome-shown')
  if (!welcomeShown) {
    showWelcome.value = true
  }
  
  // Load config with fallback to defaults
  try {
    const config = await loadConfig()
    console.log('[Init] Loaded config after setup:', config)
    isDarkMode.value = config.darkMode
    profiles.value = config.profiles.map(p => {
      // Ensure we have valid selected keypoints - check both fields and ensure not empty
      let selected = p.selected_keypoints && p.selected_keypoints.length > 0 
        ? p.selected_keypoints 
        : (p.selectedKeypoints && p.selectedKeypoints.length > 0 
          ? p.selectedKeypoints 
          : Array.from({ length: 20 }, (_, i) => i))
      
      return {
        ...p,
        selectedKeypoints: selected,
        selected_keypoints: selected,
        enabled: p.enabled !== undefined ? p.enabled : true,
      }
    })
    
    console.log('[Init] Profiles after mapping:', profiles.value)
    
    // Ensure at least one profile exists
    if (profiles.value.length === 0) {
      profiles.value = [{
        id: 'default',
        name: 'Standard Fish',
        description: 'All 20 keypoints',
        selectedKeypoints: Array.from({ length: 20 }, (_, i) => i),
        selected_keypoints: Array.from({ length: 20 }, (_, i) => i),
        createdAt: Date.now(),
        enabled: true,
        folder_path: undefined,
      }]
      activeProfileId.value = 'default'
      // Save the default profile
      await saveConfig({ ...config, profiles: profiles.value, activeProfileId: 'default' })
    } else {
      activeProfileId.value = config.activeProfileId
    }
    
    // Keep profile filter as ALL PROFILES (empty string) by default
    // This shows all images from all profiles

    // Load active profile's keypoints
    const activeProfile = profiles.value.find(p => p.id === activeProfileId.value)
    if (activeProfile) {
      selectedKeypoints.value = new Set(activeProfile.selected_keypoints || activeProfile.selectedKeypoints)
    }
  } catch (err) {
    console.error('Failed to load config after setup, using defaults:', err)
    // Fallback to default profile if config loading completely fails
    profiles.value = [{
      id: 'default',
      name: 'Standard Fish',
      description: 'All 20 keypoints',
      selectedKeypoints: Array.from({ length: 20 }, (_, i) => i),
      selected_keypoints: Array.from({ length: 20 }, (_, i) => i),
      createdAt: Date.now(),
      enabled: true,
      folder_path: undefined,
    }]
    activeProfileId.value = 'default'
    selectedProfileFilter.value = 'default'
    selectedKeypoints.value = new Set(Array.from({ length: 20 }, (_, i) => i))
  }
  
  // Re-initialize the app after setup
  initializeBackend()
  
  // Set state to idle so UI shows
  setTimeout(() => {
    if (state.value === 'loading') {
      state.value = 'idle'
    }
  }, 1000)
}

function onSetupError(message: string) {
  errorMessage.value = `Setup failed: ${message}`
}

onMounted(async () => {
  // Check if first-run setup is needed
  try {
    needsSetup.value = await checkIfSetupNeeded()
  } catch (err) {
    console.warn('Could not check setup status, assuming ready:', err)
    needsSetup.value = false
  }
  
  // If setup is not needed, continue with normal initialization
  if (!needsSetup.value) {
    // Check if welcome guide should be shown (first time user)
    const welcomeShown = localStorage.getItem('phenoai-welcome-shown')
    if (!welcomeShown) {
      showWelcome.value = true
    }
    
    // Load config with fallback to defaults
    try {
      const config = await loadConfig()
      console.log('[Init] Loaded config:', config)
      isDarkMode.value = config.darkMode
      profiles.value = config.profiles.map(p => {
        // Ensure we have valid selected keypoints - check both fields and ensure not empty
        let selected = p.selected_keypoints && p.selected_keypoints.length > 0 
          ? p.selected_keypoints 
          : (p.selectedKeypoints && p.selectedKeypoints.length > 0 
            ? p.selectedKeypoints 
            : Array.from({ length: 20 }, (_, i) => i)) // default to all 20 if missing
        
        console.log('[Init] Profile:', p.name, 'selected_keypoints:', p.selected_keypoints, 'selectedKeypoints:', p.selectedKeypoints, 'final:', selected)
        
        return {
          ...p,
          selected_keypoints: selected,
          selectedKeypoints: selected,
          enabled: p.enabled !== undefined ? p.enabled : true,
        }
      })
      
      console.log('[Init] Profiles after mapping:', profiles.value)
      
      // Ensure at least one profile exists
      if (profiles.value.length === 0) {
        profiles.value = [{
          id: 'default',
          name: 'Standard Fish',
          description: 'All 20 keypoints',
          selectedKeypoints: Array.from({ length: 20 }, (_, i) => i),
          selected_keypoints: Array.from({ length: 20 }, (_, i) => i),
          createdAt: Date.now(),
          enabled: true,
          folder_path: undefined,
        }]
        activeProfileId.value = 'default'
        // Save the default profile
        await saveConfig({ ...config, profiles: profiles.value, activeProfileId: 'default' })
      } else {
        activeProfileId.value = config.activeProfileId
      }
      
      // Keep profile filter as ALL PROFILES (empty string) by default
      // This shows all images from all profiles

      // Load active profile's keypoints
      const activeProfile = profiles.value.find(p => p.id === activeProfileId.value)
      if (activeProfile) {
        selectedKeypoints.value = new Set(activeProfile.selected_keypoints || activeProfile.selectedKeypoints)
      }
    } catch (err) {
      console.error('Failed to load config, using defaults:', err)
      // Fallback to default profile if config loading completely fails
      profiles.value = [{
        id: 'default',
        name: 'Standard Fish',
        description: 'All 20 keypoints',
        selectedKeypoints: Array.from({ length: 20 }, (_, i) => i),
        selected_keypoints: Array.from({ length: 20 }, (_, i) => i),
        createdAt: Date.now(),
        enabled: true,
        folder_path: undefined,
      }]
      activeProfileId.value = 'default'
      selectedProfileFilter.value = 'default'
      selectedKeypoints.value = new Set(Array.from({ length: 20 }, (_, i) => i))
    }

    // Initialize backend immediately but don't block UI
    initializeBackend()
    // Set state to idle after 1 second anyway so UI shows
    setTimeout(() => {
      if (state.value === 'loading') {
        state.value = 'idle'
      }
    }, 1000)
  }
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
