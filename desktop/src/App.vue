<template>
  <!-- First Run Setup View -->
  <SetupView
    v-if="needsSetup"
    @setup-complete="onSetupComplete"
    @setup-error="onSetupError"
  />

  <!-- Main App -->
  <div v-else id="app-container">

    <!-- ─── Header ──────────────────────────────────────────────── -->
    <header class="app-header">
      <div class="header-brand">
        <button class="mobile-menu-btn" @click="mobileDrawerOpen = !mobileDrawerOpen" aria-label="Open menu">☰</button>
        <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <ellipse cx="12" cy="12" rx="9" ry="5.5"/>
          <circle cx="8.5" cy="12" r="1.5" fill="currentColor" stroke="none"/>
          <path d="M21 12c-2-3-5-5.5-9-5.5" stroke-dasharray="2.5 1.5" stroke-linecap="round"/>
        </svg>
        <span class="brand-name">PhenoAI</span>
      </div>
      <div class="header-actions">
        <button class="btn-header" @click="showSettings = true">Settings</button>
        <button class="btn-header" @click="showWelcome = true">Help</button>
      </div>
    </header>

    <!-- ─── App Body: Left Panel + Workspace ─────────────────── -->
    <div class="app-body">

      <!-- Drawer backdrop (mobile) -->
      <div
        class="drawer-backdrop"
        :class="{ visible: mobileDrawerOpen }"
        @click="mobileDrawerOpen = false"
      ></div>

      <!-- Left Control Panel ─────────────────────────────────── -->
      <aside class="left-panel" :class="{ 'drawer-open': mobileDrawerOpen }">

        <!-- Banners -->
        <div v-if="errorMessage" class="panel-alert panel-alert-error">
          <span>{{ errorMessage }}</span>
          <button @click="errorMessage = ''">×</button>
        </div>
        <div v-if="infoMessage" class="panel-alert panel-alert-info">
          <span>{{ infoMessage }}</span>
          <button @click="infoMessage = ''">×</button>
        </div>

    <!-- Contribution consent banner -->
        <div v-if="showContributionBanner" class="panel-alert panel-alert-contribution">
          <div class="contribution-banner-body">
            <div class="contribution-banner-title">Help improve PhenoAI</div>
            <p class="contribution-banner-text">Share your fish images and anonymous measurements to support academic research. File system paths and personal information are <strong>never</strong> sent. Data is used exclusively to improve model accuracy.</p>
            <div class="contribution-banner-btns">
              <button class="btn-xs btn-outline" @click="acceptContribution(true)">Yes, contribute</button>
              <button class="btn-xs btn-ghost" @click="acceptContribution(false)">No thanks</button>
            </div>
          </div>
        </div>

        <!-- Dataset ──────────────────────────────────────────── -->
        <div class="panel-section">
          <div class="panel-section-title">Dataset</div>
          <div v-if="activeProfiles.length === 0" class="panel-note">
            No active profiles. Open
            <a href="#" @click.prevent="showSettings = true">Settings</a>
            to configure.
          </div>
          <div
            v-else
            v-for="profile in activeProfiles"
            :key="profile.id"
            class="dataset-row"
          >
            <div class="dataset-label">
              <span class="dataset-name">{{ profile.name }}</span>
              <span class="dataset-meta">{{ profile.selected_keypoints.length }} landmarks</span>
            </div>
            <div class="path-row">
              <span class="path-text" :title="profile.folder_path">
                {{
                  profile.folder_path
                    ? (profile.folder_path.split('/').pop() || profile.folder_path)
                    : 'No folder selected'
                }}
              </span>
              <button
                class="btn-xs btn-outline"
                @click="selectFolderForProfile(profile.id)"
                :disabled="isAnalyzing"
              >Browse</button>
              <button
                v-if="profile.folder_path"
                class="btn-xs btn-ghost"
                @click="clearFolderForProfile(profile.id)"
                title="Clear"
              >×</button>
            </div>
          </div>
        </div>

        <!-- Analysis ─────────────────────────────────────────── -->
        <div class="panel-section">
          <div class="panel-section-title">Analysis</div>
          <button
            class="btn-run"
            @click="startAnalysis"
            :disabled="!hasActiveFoldersSelected || isAnalyzing"
          >{{ isAnalyzing ? 'Running…' : 'Run Analysis' }}</button>
          <div v-if="isAnalyzing" class="analysis-status">
            <div class="progress-bar-sm">
              <div class="progress-fill-sm" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <span class="progress-label">{{ totalCount > 0 ? processedCount + ' / ' + totalCount + ' images' : 'Processing…' }}</span>
            <span v-if="currentProcessingFile" class="progress-file">
              {{ currentProcessingFile.split('/').pop() }}
            </span>
          </div>
        </div>

        <!-- Results (visible once there are predictions) ─────── -->
        <template v-if="predictions.length">
          <div class="panel-section">
            <div class="panel-section-title">Results</div>
            <div class="summary-grid">
              <div class="summary-item">
                <span class="summary-label">Specimens</span>
                <span class="summary-value">{{ filteredPredictions.length }}</span>
              </div>
              <div class="summary-item" v-if="selectedPrediction">
                <span class="summary-label">Landmarks</span>
                <span class="summary-value">{{ keypointCount }}/20</span>
              </div>
              <div class="summary-item" v-if="selectedPrediction">
                <span class="summary-label">Confidence</span>
                <span class="summary-value">{{ avgConfidence }}%</span>
              </div>
              <div class="summary-item" v-if="selectedPrediction">
                <span class="summary-label">Measures</span>
                <span class="summary-value">{{ phenotypeCount }}</span>
              </div>
            </div>
            <select
              v-if="activeProfiles.length > 1"
              v-model="selectedProfileFilter"
              class="field-select"
            >
              <option value="">All profiles</option>
              <option
                v-for="p in activeProfiles"
                :key="p.id"
                :value="p.id"
              >{{ p.name }}</option>
            </select>
          </div>

          <div class="panel-section">
            <div class="panel-section-title">Export</div>
            <div class="export-btns">
              <button class="btn-sm btn-outline" @click="exportResults('csv')">CSV</button>
              <button class="btn-sm btn-outline" @click="exportResults('json')">JSON</button>
              <button class="btn-sm btn-outline" @click="exportResults('images')">Images</button>
            </div>
            <button class="btn-text-danger" @click="clearResults">Clear results</button>
          </div>
        </template>

      </aside>

      <!-- Workspace ──────────────────────────────────────────── -->
      <main class="workspace">

        <!-- Connecting -->
        <div v-if="state === 'loading' && !predictions.length" class="workspace-loading">
          <div class="spinner"></div>
          <span>Connecting to backend…</span>
        </div>

        <!-- Getting Started (empty state) -->
        <div
          v-if="!predictions.length && !isAnalyzing && state !== 'loading'"
          class="workspace-empty"
        >
          <div class="getting-started">
            <div class="gs-title">Getting Started</div>
            <ol class="gs-steps">
              <li>Select or create a <strong>Profile</strong> in Settings</li>
              <li>Click <strong>Browse</strong> to choose an image folder</li>
              <li>Click <strong>Run Analysis</strong></li>
              <li>Review results and export data</li>
            </ol>
            <div class="gs-formats">Supported formats: JPEG · PNG · BMP · TIFF</div>
          </div>
        </div>

        <!-- Results workspace ──────────────────────────────── -->
        <div v-if="predictions.length" class="workspace-content">

          <!-- Viewer row: thumbnail strip + canvas -->
          <div class="viewer-row" :style="{ flex: '0 0 ' + viewerHeight + 'px' }">

            <!-- Thumbnail strip -->
            <div class="thumb-strip">
              <button
                v-for="(pred, idx) in filteredPredictions"
                :key="idx"
                class="thumb-item"
                :class="{ active: selectedPredictionIdx === idx }"
                @click="selectPredictionFromFiltered(idx, pred)"
                :title="getFilename(pred.image_path)"
              >
                <img
                  v-if="pred.overlay_thumbnail_base64"
                  :src="'data:image/jpeg;base64,' + pred.overlay_thumbnail_base64"
                  class="thumb-img"
                  @error="(e) => ((e.target as HTMLImageElement).style.display = 'none')"
                />
                <span v-else class="thumb-num">{{ idx + 1 }}</span>
              </button>
            </div>

            <!-- Image viewer -->
            <div class="image-viewer">
              <div class="viewer-bar">
                <span class="viewer-filename">
                  {{
                    selectedPrediction
                      ? getFilename(selectedPrediction.image_path)
                      : 'Select a specimen'
                  }}
                </span>
                <button
                  class="btn-xs btn-ghost"
                  @click="focusMode = !focusMode"
                  :title="focusMode ? 'Collapse viewer' : 'Expand viewer'"
                >{{ focusMode ? '▲' : '▼' }}</button>
              </div>
              <div class="canvas-wrap" v-if="selectedPrediction">
                <img
                  v-if="selectedPrediction.overlay_preview_base64"
                  :key="selectedPredictionIdx"
                  :src="'data:image/jpeg;base64,' + selectedPrediction.overlay_preview_base64"
                  class="preview-img"
                />
                <canvas v-else ref="previewCanvas" class="preview-canvas"></canvas>
              </div>
              <div class="canvas-empty" v-else>
                Select a specimen to preview
              </div>
            </div>

          </div><!-- /.viewer-row -->

          <!-- Drag handle to resize viewer height -->
          <div class="row-resizer" @mousedown.prevent="startRowResize($event)" title="Drag to resize"></div>

          <!-- Measurements table -->
          <div class="measurements-panel">
            <div class="measurements-bar">
              <span class="measurements-title">Measurements</span>
              <span class="measurements-count">
                {{ filteredPredictions.length }} specimens
                <template v-if="allPhenotypeKeys.length">
                  &nbsp;·&nbsp;{{ allPhenotypeKeys.length }} variables
                </template>
              </span>
              <button
                class="measures-info-btn"
                @click="showMeasuresDiagram = true"
                title="How are measurements calculated?"
              >
                <span class="measures-info-icon">ⓘ</span>
                How it's measured
              </button>
            </div>
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="th-specimen" :style="{ width: specimenColWidth + 'px', minWidth: specimenColWidth + 'px' }">
                      <div class="col-header-inner">
                        Specimen
                        <div class="col-resize-handle" @mousedown.stop.prevent="startColResize($event)"></div>
                      </div>
                    </th>
                    <th class="th-num">Landmarks</th>
                    <th class="th-num">
                      Confidence
                      <span
                        class="col-info-tip"
                        @mouseenter="showConfTip = true"
                        @mouseleave="showConfTip = false"
                        @mousemove="confTipX = $event.clientX; confTipY = $event.clientY"
                      >
                        <span class="col-info-icon">&#x24D8;</span>
                      </span>
                    </th>
                    <th
                      v-for="key in allPhenotypeKeys"
                      :key="key"
                      class="th-measure th-measure-hover"
                      @mouseenter="hoveredPhenotype = key"
                      @mouseleave="hoveredPhenotype = null"
                    >{{ key }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(pred, idx) in filteredPredictions"
                    :key="idx"
                    :class="{ 'row-selected': selectedPredictionIdx === idx }"
                    @click="selectPredictionFromFiltered(idx, pred)"
                  >
                    <td class="td-specimen" :style="{ width: specimenColWidth + 'px', maxWidth: specimenColWidth + 'px' }">{{ getFilename(pred.image_path) }}</td>
                    <td class="td-num">{{ getKeypointCount(pred) }}/20</td>
                    <td class="td-num">{{ getAvgConfidence(pred) }}%</td>
                    <td
                      v-for="key in allPhenotypeKeys"
                      :key="key"
                      class="td-measure td-measure-hover"
                      @mouseenter="hoveredPhenotype = key"
                      @mouseleave="hoveredPhenotype = null"
                    >{{ getPhenotypeValue(pred, key) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div><!-- /.measurements-panel -->

        </div><!-- /.workspace-content -->

      </main><!-- /.workspace -->

    </div><!-- /.app-body -->

    <!-- ─── Status / Log Bar ────────────────────────────────── -->
    <div class="status-bar" :class="{ 'status-expanded': showDebugConsole }">
      <template v-if="!showDebugConsole">
        <span class="status-indicator" :class="backendStatus"></span>
        <span class="status-message">
          {{
            isAnalyzing
              ? (totalCount > 0 ? `Analyzing ${processedCount}/${totalCount}…` : 'Analyzing…')
              : `Backend: ${backendStatusText}`
          }}
        </span>
        <button
          v-if="debugLogs.length"
          class="status-log-btn"
          @click="showDebugConsole = true"
        >Show log</button>
      </template>
      <template v-else>
        <div class="log-panel-header">
          <span>Log</span>
          <div>
            <button class="btn-xs btn-ghost" @click="debugLogs = []">Clear</button>
            <button class="btn-xs btn-ghost" @click="showDebugConsole = false">Close</button>
          </div>
        </div>
        <div class="log-panel-body">
          <div
            v-for="(log, idx) in debugLogs.slice(-100)"
            :key="idx"
            class="log-entry"
            :class="log.level"
          >
            <span class="log-time">{{ log.time }}</span>
            <span>{{ log.message }}</span>
          </div>
        </div>
      </template>
    </div>

    <!-- ─── Footer ──────────────────────────────────────────── -->
    <footer class="app-footer">
      <span>PhenoAI v0.1.0</span>
      <span class="footer-sep">·</span>
      <span>Backend: <span :class="backendStatus">{{ backendStatusText }}</span></span>
    </footer>

    <!-- Confidence tooltip -->
    <teleport to="body">
      <div
        v-if="showConfTip"
        class="conf-tooltip"
        :style="{ top: confTipY - 8 + 'px', left: confTipX + 'px' }"
      >
        The average keypoint confidence score output by the ViTPose model.
        For each detected keypoint, the model produces a heatmap and the peak
        activation value is used as the confidence score (0–100%).
        A higher value means the model is more certain about the keypoint’s
        position. Low scores can indicate occlusion, poor image quality,
        or the keypoint being near the frame edge.
      </div>
    </teleport>

    <!-- Measures diagram lightbox -->
    <div
      v-if="showMeasuresDiagram"
      class="measures-lightbox-overlay"
      @click="showMeasuresDiagram = false"
      @keydown.esc="showMeasuresDiagram = false"
      tabindex="0"
    >
      <div class="measures-lightbox-inner" @click.stop>
        <div class="measures-lightbox-header">
          <span class="measures-lightbox-title">How measurements are calculated</span>
          <button class="measures-lightbox-close" @click="showMeasuresDiagram = false">&times;</button>
        </div>
        <img
          :src="`${baseUrl}measures-diagram.jpg`"
          alt="Measurements diagram"
          class="measures-lightbox-img"
        />
        <div class="measures-lightbox-reference">
          <span class="measures-lightbox-reference-label">Recommended photography system:</span>
          <span class="measures-lightbox-reference-authors">García-Melo et al.</span>
          <button class="measures-lightbox-reference-link" @click="openPhotafishArticle">
            Photafish system: An affordable device for fish photography in the wild
          </button>
          <span class="measures-lightbox-reference-journal">Zootaxa 4554(1), 2019</span>
        </div>
      </div>
    </div>

    <!-- Settings Modal -->
    <SettingsModal
      :isOpen="showSettings"
      :profiles="profiles"
      :activeProfileId="activeProfileId"
      :keypointNames="modelInfo?.keypoint_names || []"
      :contributionOptIn="contributionOptIn"
      @close="showSettings = false"
      @save="handleSettingsSave"
      @delete="handleDeleteProfile"
      @contribution-change="handleContributionChange"
    />

    <!-- Welcome Guide -->
    <WelcomeGuide
      :show="showWelcome"
      @close="showWelcome = false"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import {
  isTauri,
  openDialog,
  openExternal,
  readBinaryFile,
  resolveImageUrl,
  homeDir,
  tauriInvoke,
  getBackendUrl as platformGetBackendUrl,
} from './utils/platform'
import type { PredictionResult, ModelInfo, AnalysisState, Profile } from './types'
import { 
  analyzeFolder, 
  getModelInfo, 
  exportCSV, 
  exportJSON, 
  exportAnnotatedImages,
  downloadExport,
  resetBackendUrl 
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
  setContributionOptIn,
  getOrCreateAnonymousId,
  PRESET_PROFILES,
} from './utils/storage'
import { uploadContributions } from './utils/contribution'

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
const showMeasuresDiagram = ref(false)
const mobileDrawerOpen = ref(false)
const baseUrl = (import.meta as any).env?.BASE_URL || '/'

function openPhotafishArticle() {
  openExternal('https://www.mapress.com/zt/article/view/zootaxa.4554.1.4')
}
const showConfTip = ref(false)
const confTipX = ref(0)
const confTipY = ref(0)
const hoveredPhenotype = ref<string | null>(null)
const showDebugConsole = ref(false)
const debugLogs = ref<Array<{time: string, level: string, message: string}>>([])
const profiles = ref<Profile[]>([])
const activeProfileId = ref(PRESET_PROFILES[0].id)
const selectedKeypoints = ref<Set<number>>(new Set())
const selectedProfileFilter = ref('')
const showWelcome = ref(false)
const contributionOptIn = ref(false)
const anonymousId = ref('')
const showContributionBanner = ref(false)
const pendingContributionBatch = ref<PredictionResult[]>([])

// Resizable panels
const viewerHeight = ref(460)      // px — draggable row height
const specimenColWidth = ref(200)  // px — draggable specimen column width

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

// All unique phenotype keys across the current filtered predictions (for table columns).
// - Specific profile selected: only columns where both KPs are in that profile.
// - "All profiles" (no filter): union of all valid columns across every row,
//   each row gated by its own profile. Cells that don't apply show '—'.
const allPhenotypeKeys = computed(() => {
  // Always derive column list from the canonical modelInfo — never from stale prediction names
  const names = modelInfo.value?.phenotype_names
  const pairs = modelInfo.value?.phenotype_pairs
  if (!names || !pairs || names.length === 0) return []

  if (selectedProfileFilter.value) {
    // Single profile view — only columns where both KPs belong to the profile
    const activeProfile = profiles.value.find(p => p.id === selectedProfileFilter.value)
    const selectedKpts = activeProfile ? new Set(activeProfile.selected_keypoints) : null
    return names.filter((_, idx) => {
      if (!selectedKpts) return true
      const pair = pairs[idx]
      return pair ? selectedKpts.has(pair[0]) && selectedKpts.has(pair[1]) : true
    })
  } else {
    // All profiles — show column if at least one profile covers both KPs
    if (profiles.value.length === 0) return names
    return names.filter((_, idx) => {
      const pair = pairs[idx]
      if (!pair) return true
      return profiles.value.some(prof => {
        const kpts = new Set(prof.selected_keypoints)
        return kpts.has(pair[0]) && kpts.has(pair[1])
      })
    })
  }
})

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

async function getImageDataUrl(imagePath: string): Promise<string> {
  if (!imagePath) return ''
  return resolveImageUrl(imagePath)
}

function getPhenotypeValue(pred: PredictionResult, phenotypeName: string): string {
  // Resolve canonical index from modelInfo — decoupled from stale prediction names
  const names = modelInfo.value?.phenotype_names || []
  const pairs = modelInfo.value?.phenotype_pairs || []
  const idx = names.indexOf(phenotypeName)
  if (idx === -1) return '—'

  // Gate by the prediction's own profile
  const predProfileId = (pred as any).profile_id
  const predProfile = predProfileId ? profiles.value.find(p => p.id === predProfileId) : null
  if (predProfile) {
    const predKpts = new Set(predProfile.selected_keypoints)
    const pair = pairs[idx]
    if (pair && (!predKpts.has(pair[0]) || !predKpts.has(pair[1]))) return '—'
  }

  // Find by id (stable index) first, fall back to name match for older data
  const phenos: any[] = pred.extra_pred_fields?.phenotypes || []
  const pheno = phenos.find((p: any) => p.id === idx) ?? phenos.find((p: any) => p.name === phenotypeName)
  if (!pheno || typeof pheno.value_px !== 'number') return '—'
  return pheno.value_px.toFixed(2)
}

function selectPrediction(idx: number) {
  selectedPredictionIdx.value = idx
  loadPreviewForIdx(idx)
}

function selectPredictionFromFiltered(idx: number, pred: PredictionResult) {
  selectedPredictionIdx.value = idx
  // Keep current profile filter selection (don't auto-switch)
  loadPreviewForIdx(idx)
}

function deselectImage(idx: number) {
  predictions.value.splice(idx, 1)
  if (selectedPredictionIdx.value >= predictions.value.length) {
    selectedPredictionIdx.value = Math.max(0, predictions.value.length - 1)
  }
  if (predictions.value.length > 0) {
    loadPreviewForIdx(selectedPredictionIdx.value)
  } else {
    selectedPredictionIdx.value = -1
  }
}


async function selectFolderForProfile(profileId: string) {
  try {
    const selected = await openDialog({
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
  mobileDrawerOpen.value = false
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

    // Keep profile filter as ALL PROFILES (empty string) by default
    // User can manually select a specific profile if needed

    state.value = 'complete'
    infoMessage.value = `Analysis complete! Processed ${totalProcessed} images.`

    // Fire anonymous contributions sequentially in background (one image at a time)
    if (contributionOptIn.value && anonymousId.value) {
      const logger = { log: console.log, warn: console.warn }
      uploadContributions(allPredictions, anonymousId.value, logger)
    }
    // Show contribution banner after every analysis if the user hasn't opted in yet
    if (!contributionOptIn.value) {
      pendingContributionBatch.value = [...allPredictions]
      showContributionBanner.value = true
    }

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
  
  // Get keypoints and scores
  let kpts = pred.keypoints || []
  let scores = pred.keypoint_scores || []
  
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
  
  // Filter phenotypes - only include if both keypoints are selected
  const phenotypes = pred.extra_pred_fields?.phenotypes || []
  const filteredPhenotypes = phenotypes.filter(p => {
    const [kp1, kp2] = modelInfo.value?.phenotype_pairs?.[p.id] || [p.pair[0], p.pair[1]]
    return selectedKpts.has(kp1) && selectedKpts.has(kp2)
  })
  
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

      // Filter predictions to only include selected keypoints and phenotypes
      const filteredPreds = profilePreds.map(pred => filterPredictionsByProfile(pred, profile))

      if (!isTauri) {
        // Web mode — download via browser
        await downloadExport(format, filteredPreds, profile.name)
        infoMessage.value = `Downloaded ${profile.name} ${format.toUpperCase()} export`
        continue
      }

      // Tauri desktop — write to filesystem
      let outputPath = ''

      if (format === 'images') {
        const baseDir = await openDialog({
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

// Lazy-load overlay preview from disk when the user selects a prediction.
// The batch response omits overlay_preview_base64 to keep the JSON response small;
// we read the JPEG from overlay_path only for the one image being viewed.
async function loadPreviewForIdx(idx: number) {
  const pred = predictions.value[idx]
  if (!pred) return
  // Already cached — let the reactive <img> element render it
  if (pred.overlay_preview_base64) { drawPreview(); return }
  // No overlay on disk — canvas fallback
  if (!pred.overlay_path) { drawPreview(); return }
  try {
    const bytes = await readBinaryFile(pred.overlay_path)
    const uint8 = new Uint8Array(bytes)
    let binary = ''
    const CHUNK = 8192
    for (let i = 0; i < uint8.length; i += CHUNK) {
      binary += String.fromCharCode(...uint8.subarray(i, i + CHUNK))
    }
    // Cache in the prediction object so re-selecting doesn't re-read the file
    predictions.value[idx] = { ...predictions.value[idx], overlay_preview_base64: btoa(binary) }
    // Vue reactive update triggers the <img> element automatically
  } catch {
    drawPreview() // canvas fallback on read error
  }
}

function drawPreview() {
  // overlay_preview_base64 → the <img> element handles it reactively, no canvas needed.
  if (selectedPrediction.value?.overlay_preview_base64) return
  if (!previewCanvas.value || !selectedPrediction.value) return

  const canvas = previewCanvas.value
  const pred = selectedPrediction.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const rect = canvas.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  const displayWidth = Math.max(rect.width || 800, 800)
  const displayHeight = Math.max(rect.height || 600, 600)
  canvas.width = displayWidth * dpr
  canvas.height = displayHeight * dpr
  canvas.style.width = displayWidth + 'px'
  canvas.style.height = displayHeight + 'px'
  ctx.scale(dpr, dpr)

  function drawLoadedImage(img: HTMLImageElement) {
    const w = canvas.width / dpr
    const h = canvas.height / dpr
    const scale = Math.min(w / img.width, h / img.height)
    const sw = img.width * scale
    const sh = img.height * scale
    const ox = (w - sw) / 2
    const oy = (h - sh) / 2
    ctx.fillStyle = '#F5F6F8'
    ctx.fillRect(0, 0, w, h)
    ctx.drawImage(img, ox, oy, sw, sh)
    drawKeypointsOnCanvas(ctx, pred, canvas, img, scale, ox, oy, dpr)
  }

  function drawFallbackGray() {
    ctx.fillStyle = '#F5F6F8'
    ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr)
    drawKeypointsOnCanvas(ctx, pred, canvas, null, 1, 0, 0, dpr)
  }

  // Load original image from disk and draw keypoints on canvas
  const imagePath = pred.image_path
  if (!imagePath) { drawFallbackGray(); return }

  const img = new Image()
  img.onload = () => drawLoadedImage(img)
  img.onerror = () => drawFallbackGray()
  img.crossOrigin = 'anonymous'
  resolveImageUrl(imagePath).then(url => { img.src = url })
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

  // ── Measurement line overlay on hover ──────────────────────────────────
  const hovered = hoveredPhenotype.value
  if (hovered && pred.extra_pred_fields?.phenotypes) {
    // Look up by canonical index first (robust against stale prediction names)
    const _hovIdx = (modelInfo.value?.phenotype_names || []).indexOf(hovered)
    const pheno = _hovIdx !== -1
      ? pred.extra_pred_fields.phenotypes.find((p: any) => p.id === _hovIdx)
        ?? pred.extra_pred_fields.phenotypes.find((p: any) => p.name === hovered)
      : pred.extra_pred_fields.phenotypes.find((p: any) => p.name === hovered)
    if (pheno) {
      const [kp1, kp2] = modelInfo.value?.phenotype_pairs?.[pheno.id] || [pheno.pair[0], pheno.pair[1]]
      const kpts = keypoints  // already flattened above

      const kpt1 = kpts[kp1]
      const kpt2 = kpts[kp2]
      if (kpt1 && kpt2) {
        const x1 = offsetX + Number(kpt1[0]) * scale
        const y1 = offsetY + Number(kpt1[1]) * scale
        const x2 = offsetX + Number(kpt2[0]) * scale
        const y2 = offsetY + Number(kpt2[1]) * scale

        const canvasAvg = (canvas.width + canvas.height) / (2 * dpr)
        const lw = Math.max(1.5, canvasAvg / 250)
        const distType: string = pheno.type || 'xy'

        ctx.save()
        ctx.setLineDash([lw * 3, lw * 2])
        ctx.strokeStyle = 'rgba(255, 220, 0, 0.92)'
        ctx.lineWidth = lw
        ctx.shadowColor = 'rgba(0, 0, 0, 0.7)'
        ctx.shadowBlur = lw * 2

        let mx: number, my: number  // label midpoint

        if (distType === 'x') {
          // Horizontal line at y-midpoint, spanning x1→x2, with vertical end-ticks
          const ym = (y1 + y2) / 2
          ctx.beginPath(); ctx.moveTo(x1, ym); ctx.lineTo(x2, ym); ctx.stroke()
          ctx.setLineDash([])
          ctx.shadowBlur = 0
          ctx.beginPath(); ctx.moveTo(x1, ym - lw * 5); ctx.lineTo(x1, ym + lw * 5); ctx.stroke()
          ctx.beginPath(); ctx.moveTo(x2, ym - lw * 5); ctx.lineTo(x2, ym + lw * 5); ctx.stroke()
          mx = (x1 + x2) / 2; my = ym
        } else if (distType === 'y') {
          // Vertical line at x-midpoint, spanning y1→y2, with horizontal end-ticks
          const xm = (x1 + x2) / 2
          ctx.beginPath(); ctx.moveTo(xm, y1); ctx.lineTo(xm, y2); ctx.stroke()
          ctx.setLineDash([])
          ctx.shadowBlur = 0
          ctx.beginPath(); ctx.moveTo(xm - lw * 5, y1); ctx.lineTo(xm + lw * 5, y1); ctx.stroke()
          ctx.beginPath(); ctx.moveTo(xm - lw * 5, y2); ctx.lineTo(xm + lw * 5, y2); ctx.stroke()
          mx = xm; my = (y1 + y2) / 2
        } else {
          // Euclidean: straight diagonal line
          ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
          ctx.setLineDash([])
          ctx.shadowBlur = 0
          mx = (x1 + x2) / 2; my = (y1 + y2) / 2
        }

        // Value label pill at midpoint
        const fs = Math.max(11, canvasAvg / 55)
        const label = `${hovered}: ${typeof pheno.value_px === 'number' ? pheno.value_px.toFixed(1) + 'px' : '—'}`
        ctx.font = `bold ${fs}px sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        const tw = ctx.measureText(label).width
        const pad = fs * 0.45
        ctx.fillStyle = 'rgba(20, 20, 20, 0.72)'
        ctx.beginPath()
        ctx.roundRect(mx - tw / 2 - pad, my - fs * 0.7, tw + pad * 2, fs * 1.4, fs * 0.35)
        ctx.fill()
        ctx.fillStyle = 'rgba(255, 220, 0, 1)'
        ctx.fillText(label, mx, my)
        ctx.restore()
      }
    }
  }

}

// Track retry timer so it can be cancelled on unmount
let _retryTimer: ReturnType<typeof setTimeout> | null = null

async function initializeBackend() {
  const maxRetries = 12  // 12 * 2s = 24 seconds max wait
  let retries = 0
  
  const attemptConnection = async () => {
    try {
      // In Tauri mode, force backend startup and URL registration before the first HTTP call.
      if (isTauri) {
        await tauriInvoke<string>('ensure_backend_running')
      }

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
        _retryTimer = window.setTimeout(attemptConnection, 2000)
      } else {
        // Max retries reached - show error
        console.error('Failed to connect to backend after max retries:', err)
        errorMessage.value = `Backend connection error: ${errorDetails}`
        state.value = 'idle'
        backendReady.value = false
        // Try one more time after 10 seconds in case backend is slow
        _retryTimer = window.setTimeout(attemptConnection, 10000)
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
    const p = profiles.value.find(pr => pr.id === profileId)
    if (p?.isBuiltIn) return
    await deleteProfile(profileId)
    profiles.value = profiles.value.filter(p => p.id !== profileId)
    
    // If deleted profile was active, switch to first preset
    if (activeProfileId.value === profileId) {
      activeProfileId.value = PRESET_PROFILES[0].id
      await setActiveProfile(PRESET_PROFILES[0].id)
    }
    
    infoMessage.value = 'Profile deleted'
  } catch (err) {
    errorMessage.value = `Failed to delete profile: ${err}`
  }
}

// Setup handlers
async function checkIfSetupNeeded(): Promise<boolean> {
  if (!isTauri) return false  // Web mode — backend is pre-configured
  try {
    return await tauriInvoke<boolean>('check_setup_needed')
  } catch (err) {
    console.error('Failed to check setup status:', err)
    // Assume setup is NOT needed if we can't check (dev mode)
    return false
  }
}

async function handleContributionChange(value: boolean) {
  contributionOptIn.value = value
  await setContributionOptIn(value)
}

async function acceptContribution(value: boolean) {
  showContributionBanner.value = false
  await handleContributionChange(value)
  // If the user just opted in, immediately upload the batch from this analysis
  if (value && pendingContributionBatch.value.length && anonymousId.value) {
    const logger = { log: console.log, warn: console.warn }
    uploadContributions(pendingContributionBatch.value, anonymousId.value, logger)
  }
  pendingContributionBatch.value = []
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
    
    // Ensure at least one profile exists
    if (profiles.value.length === 0) {
      profiles.value = [...PRESET_PROFILES]
      activeProfileId.value = PRESET_PROFILES[0].id
      // Save the default profile
      await saveConfig({ ...config, profiles: profiles.value, activeProfileId: PRESET_PROFILES[0].id })
    } else {
      activeProfileId.value = config.activeProfileId
    }

    // Load active profile's keypoints
    const activeProfile = profiles.value.find(p => p.id === activeProfileId.value)
    if (activeProfile) {
      selectedKeypoints.value = new Set(activeProfile.selected_keypoints || activeProfile.selectedKeypoints)
    }
    contributionOptIn.value = config.contributionOptIn ?? false
    anonymousId.value = await getOrCreateAnonymousId()
  } catch (err) {
    console.error('Failed to load config after setup, using defaults:', err)
    // Fallback to default profile if config loading completely fails
    profiles.value = [...PRESET_PROFILES]
    activeProfileId.value = PRESET_PROFILES[0].id
    selectedProfileFilter.value = PRESET_PROFILES[0].id
    selectedKeypoints.value = new Set(PRESET_PROFILES[0].selected_keypoints)
  }
  
  // Re-initialize the app after setup
  resetBackendUrl()
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

// ── Resize handlers ──────────────────────────────────────────────────────────

/** Drag the horizontal divider between the viewer row and the measurements panel */
function startRowResize(e: MouseEvent) {
  const startY = e.clientY
  const startH = viewerHeight.value
  const onMove = (ev: MouseEvent) => {
    const dy = ev.clientY - startY
    viewerHeight.value = Math.max(160, Math.min(startH + dy, window.innerHeight - 220))
  }
  const onUp = () => {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }
  document.body.style.cursor = 'row-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

/** Drag the right edge of the Specimen column header to resize it */
function startColResize(e: MouseEvent) {
  const startX = e.clientX
  const startW = specimenColWidth.value
  const onMove = (ev: MouseEvent) => {
    const dx = ev.clientX - startX
    specimenColWidth.value = Math.max(80, Math.min(startW + dx, 520))
  }
  const onUp = () => {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
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
      isDarkMode.value = config.darkMode
      profiles.value = config.profiles.map(p => {
        // Ensure we have valid selected keypoints - check both fields and ensure not empty
        let selected = p.selected_keypoints && p.selected_keypoints.length > 0 
          ? p.selected_keypoints 
          : (p.selectedKeypoints && p.selectedKeypoints.length > 0 
            ? p.selectedKeypoints 
            : Array.from({ length: 20 }, (_, i) => i)) // default to all 20 if missing
        
        return {
          ...p,
          selected_keypoints: selected,
          selectedKeypoints: selected,
          enabled: p.enabled !== undefined ? p.enabled : true,
        }
      })
      
      // Ensure at least one profile exists
      if (profiles.value.length === 0) {
        profiles.value = [...PRESET_PROFILES]
        activeProfileId.value = PRESET_PROFILES[0].id
        // Save the default profile
        await saveConfig({ ...config, profiles: profiles.value, activeProfileId: PRESET_PROFILES[0].id })
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
      contributionOptIn.value = config.contributionOptIn ?? false
      anonymousId.value = await getOrCreateAnonymousId()
    } catch (err) {
      console.error('Failed to load config, using defaults:', err)
      // Fallback to preset profiles if config loading completely fails
      profiles.value = [...PRESET_PROFILES]
      activeProfileId.value = PRESET_PROFILES[0].id
      selectedProfileFilter.value = PRESET_PROFILES[0].id
      selectedKeypoints.value = new Set(PRESET_PROFILES[0].selected_keypoints)
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

onBeforeUnmount(() => {
  if (_retryTimer !== null) { clearTimeout(_retryTimer); _retryTimer = null }
})

watch(() => selectedPredictionIdx.value, async () => {
  await nextTick()
  loadPreviewForIdx(selectedPredictionIdx.value)
})

// Reset selection when filtering by profile
watch(() => selectedProfileFilter.value, () => {
  selectedPredictionIdx.value = 0
})

// Redraw canvas when measurement is hovered so the overlay line appears
watch(hoveredPhenotype, () => {
  drawPreview()
})

// Auto-draw preview when predictions become available
watch(() => filteredPredictions.value.length, async () => {
  if (filteredPredictions.value.length > 0) {
    await nextTick()
    loadPreviewForIdx(selectedPredictionIdx.value)
  }
})
</script>

<style scoped>
/* CSS will be in main.css */
</style>
