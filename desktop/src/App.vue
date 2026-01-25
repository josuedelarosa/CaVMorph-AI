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
          <button class="icon-btn" @click="isDarkMode = !isDarkMode" title="Toggle dark mode">
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
          <div class="control-group">
            <button class="btn btn-primary" @click="selectFolder" :disabled="isAnalyzing">
              📁 Select Folder
            </button>
            <span v-if="folderPath" class="selected-path">{{ folderPath }}</span>
            <span v-else class="text-muted">No folder selected</span>
          </div>
        </section>

        <!-- Analysis Button -->
        <section v-if="folderPath && state !== 'analyzing'" class="control-section">
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
            <span>Processing: {{ processedCount }} / {{ totalCount }} images</span>
            <span class="time-est" v-if="totalCount > 0">
              ~{{ estimatedTimeRemaining }}s remaining
            </span>
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
            <h2>📊 Results ({{ predictions.length }} images)</h2>
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

          <!-- Preview -->
          <div v-if="selectedPrediction" class="preview-section">
            <h3>Preview: {{ selectedPredictionFilename }}</h3>
            <div class="preview-container">
              <canvas 
                ref="previewCanvas"
                class="preview-canvas"
              ></canvas>
              <div class="preview-info">
                <p><strong>Image:</strong> {{ selectedPrediction.image_path }}</p>
                <p><strong>Keypoints Detected:</strong> {{ keypointCount }} / 20</p>
                <p v-if="phenotypeCount > 0">
                  <strong>Phenotypes:</strong> {{ phenotypeCount }}
                </p>
              </div>
            </div>
          </div>

          <!-- Data Table -->
          <div class="table-section">
            <h3>Phenotype Measurements</h3>
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="col-image">Image</th>
                    <th v-for="pheno in phenotypeColumns" :key="pheno">
                      {{ pheno }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="(pred, idx) in predictions" 
                    :key="idx"
                    :class="{ active: selectedPredictionIdx === idx }"
                    @click="selectPrediction(idx)"
                  >
                    <td class="col-image">
                      <button class="filename-btn">
                        {{ getFilename(pred.image_path) }}
                      </button>
                    </td>
                    <td v-for="pheno in phenotypeColumns" :key="pheno">
                      {{ getPhenotypeValue(pred, pheno) }}
                    </td>
                  </tr>
                </tbody>
              </table>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { open } from '@tauri-apps/api/dialog'
import type { PredictionResult, ModelInfo, AnalysisState } from './types'
import { 
  analyzeFolder, 
  getModelInfo, 
  exportCSV, 
  exportJSON, 
  exportAnnotatedImages 
} from './utils/api'

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
const modelInfo = ref<ModelInfo | null>(null)
const backendReady = ref(false)
const previewCanvas = ref<HTMLCanvasElement | null>(null)

// Computed
const selectedPrediction = computed(() => 
  predictions.value[selectedPredictionIdx.value] || null
)

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
  return selectedPrediction.value.extra_pred_fields.phenotypes.map(p => p.name)
})

const backendStatusText = computed(() => 
  backendReady.value ? 'Ready' : 'Connecting...'
)

const backendStatus = computed(() =>
  backendReady.value ? 'status-ready' : 'status-pending'
)

const keypointCount = computed(() => {
  if (!selectedPrediction.value) return 0
  const scores = selectedPrediction.value.keypoint_scores || []
  // Handle nested arrays: [[score1, score2, ...]] -> [score1, score2, ...]
  if (Array.isArray(scores) && scores.length > 0 && Array.isArray(scores[0])) {
    return scores[0].length
  }
  return scores.length
})

const phenotypeCount = computed(() => {
  if (!selectedPrediction.value) return 0
  return selectedPrediction.value.extra_pred_fields?.phenotypes?.length || 0
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

async function selectFolder() {
  try {
    const selected = await open({
      directory: true,
      multiple: false,
    })
    if (selected && typeof selected === 'string') {
      folderPath.value = selected
    }
  } catch (err) {
    errorMessage.value = `Failed to select folder: ${err}`
  }
}

async function startAnalysis() {
  if (!folderPath.value) {
    errorMessage.value = 'Please select a folder first'
    return
  }

  try {
    isAnalyzing.value = true
    state.value = 'analyzing'
    predictions.value = []
    processedCount.value = 0
    totalCount.value = 0
    errorMessage.value = ''
    infoMessage.value = 'Starting analysis...'

    const result = await analyzeFolder(folderPath.value, true)
    
    predictions.value = result.predictions
    processedCount.value = result.count
    totalCount.value = result.count
    
    state.value = 'complete'
    infoMessage.value = `Analysis complete! Processed ${result.count} images.`
    
    if (predictions.value.length > 0) {
      selectPrediction(0)
    }
  } catch (err) {
    state.value = 'error'
    errorMessage.value = `Analysis failed: ${err}`
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
    let filename = `fish_morphometrics_${timestamp}`
    let outputPath = ''

    if (format === 'images') {
      const dir = await open({
        directory: true,
        defaultPath: folderPath.value,
      })
      if (!dir || typeof dir !== 'string') return
      outputPath = dir
    } else {
      // In a real app, would use file dialog
      outputPath = `/tmp/${filename}.${format}`
    }

    if (format === 'csv') {
      await exportCSV(outputPath, predictions.value)
    } else if (format === 'json') {
      await exportJSON(outputPath, predictions.value)
    } else if (format === 'images') {
      await exportAnnotatedImages(outputPath, predictions.value)
    }

    infoMessage.value = `Exported to ${outputPath}`
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

  // Set canvas size
  canvas.width = 300
  canvas.height = 400

  // Clear canvas
  ctx.fillStyle = '#f0f0f0'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // Try to load and draw image from file path
  const imagePath = pred.image_path
  console.log('drawCanvas - imagePath:', imagePath)
  
  if (imagePath) {
    const img = new Image()
    // Use file:// protocol for local files
    const fileUrl = 'file://' + imagePath
    console.log('Creating Image, setting src to:', fileUrl)
    
    img.src = fileUrl
    
    img.onload = () => {
      console.log('Image loaded successfully:', imagePath)
      // Clear canvas before drawing image
      ctx.fillStyle = '#f0f0f0'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      
      // Draw image scaled to canvas
      const scaleX = canvas.width / img.width
      const scaleY = canvas.height / img.height
      const scale = Math.min(scaleX, scaleY)
      
      const scaledWidth = img.width * scale
      const scaledHeight = img.height * scale
      const x = (canvas.width - scaledWidth) / 2
      const y = (canvas.height - scaledHeight) / 2
      
      console.log('Drawing image:', { width: img.width, height: img.height, scale, x, y })
      ctx.drawImage(img, x, y, scaledWidth, scaledHeight)
      
      // Draw keypoints on top of image
      drawKeypointsOnCanvas(ctx, pred, canvas, img, scale, x, y)
    }
    
    img.onerror = (e) => {
      console.error('Failed to load image:', imagePath, e)
      console.log('Falling back to keypoints only on gray background')
      // If image fails to load, just draw keypoints on gray background
      drawKeypointsOnCanvas(ctx, pred, canvas, null, 1, 0, 0)
    }
  } else {
    console.warn('No image path provided')
    // No image path, just draw keypoints
    drawKeypointsOnCanvas(ctx, pred, canvas, null, 1, 0, 0)
  }
}

function drawKeypointsOnCanvas(
  ctx: CanvasRenderingContext2D,
  pred: PredictionResult,
  canvas: HTMLCanvasElement,
  img: HTMLImageElement | null,
  scale: number,
  offsetX: number,
  offsetY: number
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

  const maxPoints = Math.min(keypoints.length, scores.length)
  
  for (let i = 0; i < maxPoints; i++) {
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
    ctx.fillText(`Avg Confidence: ${confText}`, 10, canvas.height - 10)
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

onMounted(async () => {
  // Initialize immediately but don't block UI
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
</script>

<style scoped>
/* CSS will be in main.css */
</style>
