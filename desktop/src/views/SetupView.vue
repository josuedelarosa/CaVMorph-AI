<template>
  <div class="setup-container">
    <div class="setup-card">
      <div class="header">
        <div class="logo-icon">🐟</div>
        <h1>PhenoAI</h1>
        <p class="subtitle">First-time Setup</p>
      </div>

      <!-- Pre-setup: system check summary -->
      <div v-if="!setupStarted && !setupComplete" class="choice-screen">
        <div class="choice-header">
          <h2>Environment Check</h2>
          <p>PhenoAI needs a Python runtime and model files. In installer builds, Python can be bundled automatically.</p>
        </div>

        <div class="environment-check">
          <!-- Python -->
          <div class="check-item" :class="pythonPath ? 'success' : 'warning'">
            <span class="check-icon">{{ pythonPath ? '✓' : '✗' }}</span>
            <span v-if="pythonPath">Python found: {{ pythonPath }}</span>
            <span v-else>Python runtime not found (bundled or system)</span>
          </div>
          <!-- Dependencies -->
          <div class="check-item" :class="depsInstalled ? 'success' : 'warning'" v-if="pythonPath">
            <span class="check-icon">{{ depsInstalled ? '✓' : '⚠' }}</span>
            <span v-if="depsInstalled">ONNX runtime packages installed</span>
            <span v-else>ONNX runtime packages need to be installed</span>
          </div>
          <!-- Model -->
          <div class="check-item" :class="modelDir ? 'success' : 'warning'">
            <span class="check-icon">{{ modelDir ? '✓' : '⚠' }}</span>
            <span v-if="modelDir">Model files found</span>
            <span v-else>Model files not found</span>
          </div>
          <!-- Runtime scripts -->
          <div class="check-item" :class="runtimeDir ? 'success' : 'warning'">
            <span class="check-icon">{{ runtimeDir ? '✓' : '⚠' }}</span>
            <span v-if="runtimeDir">Inference runtime found</span>
            <span v-else>Inference runtime files missing</span>
          </div>
        </div>

        <!-- If everything is ready, offer to start immediately -->
        <div v-if="pythonPath && depsInstalled && modelDir && runtimeDir" class="all-ready">
          <p class="ready-message">✅ Everything looks good!</p>
          <button @click="startApp" class="btn-primary" :disabled="launchInProgress">
            {{ launchInProgress ? 'Starting…' : 'Start Application' }}
          </button>
        </div>

        <!-- If deps or venv are missing but Python + model OK -->
        <div v-else-if="pythonPath && modelDir && runtimeDir" class="needs-install">
          <p class="info-message">Some dependencies need to be installed. This usually takes 1–2 minutes.</p>
          <button @click="runSetup" class="btn-primary">Install Dependencies</button>
        </div>

        <!-- Runtime missing -->
        <div v-else-if="pythonPath && modelDir && !runtimeDir" class="needs-model">
          <div class="help-text">
            <p><strong>Inference runtime files are missing from this installation.</strong>
              This is not a Python dependency issue. Reinstall PhenoAI using the latest installer package,
              then click Check Again.
              <br>If this persists, click "View Full Logs" and share launcher.log.</p>
          </div>
          <div class="actions" style="margin-top:16px">
            <button @click="checkEnvironment" class="btn-secondary">Check Again</button>
            <button @click="openLogs" class="btn-secondary">View Full Logs</button>
          </div>
        </div>

        <!-- Python missing -->
        <div v-else-if="!pythonPath" class="needs-python">
          <div class="help-text">
            <p><strong>No Python runtime was found.</strong>
              If you installed from the official PhenoAI installer, reinstall with the bundled runtime package.
              For source/dev runs, install Python 3.9+ or set PHENOAI_PYTHON to a valid interpreter, then restart PhenoAI.</p>
          </div>
          <div class="actions" style="margin-top:16px">
            <button @click="checkEnvironment" class="btn-secondary">Check Again</button>
          </div>
        </div>

        <!-- Model missing -->
        <div v-else-if="!modelDir" class="needs-model">
          <div class="help-text">
            <p><strong>Model files not found.</strong>
              Place <strong>model.onnx</strong> and <strong>model_metadata.json</strong> in one of these folders:
              <br>• %APPDATA%\PhenoAI\models\cavfish_v1
              <br>• {project}/models/cavfish_v1 (source/dev runs)
              <br>Then click Check Again or restart PhenoAI.</p>
          </div>
          <div class="actions" style="margin-top:16px">
            <button @click="checkEnvironment" class="btn-secondary">Check Again</button>
          </div>
        </div>
      </div>

      <!-- Progress steps -->
      <div v-if="setupStarted" class="progress-section">
        <div class="steps-grid">
          <div class="step" v-for="(step, index) in steps" :key="index"
               :class="{ active: currentStep === index, completed: currentStep > index, error: step.error }">
            <div class="step-icon">
              <span v-if="currentStep > index && !step.error">✓</span>
              <span v-else-if="step.error">✗</span>
              <span v-else-if="currentStep === index" class="spinner">⏳</span>
              <span v-else>{{ index + 1 }}</span>
            </div>
            <div class="step-content">
              <div class="step-title">{{ step.title }}</div>
              <div class="step-description" v-if="currentStep === index">{{ step.description }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Log viewer -->
      <div v-if="setupStarted || logs.length > 0 || setupError || launchInProgress" class="log-section" v-show="logs.length > 0 || launchInProgress || setupError">
        <div class="log-header">Diagnostics</div>
        <div class="log-content" ref="logContainer">
          <div v-for="(log, i) in logs" :key="i" :class="['log-line', log.level]">
            {{ log.message }}
          </div>
          <div v-if="launchInProgress && logs.length === 0" class="log-line">Starting backend…</div>
        </div>
      </div>

      <!-- Status bar -->
      <div v-if="setupStarted || launchInProgress || setupError" class="status-bar">
        <div class="status-text">{{ statusMessage }}</div>
        <div class="progress-bar" v-if="!setupComplete && !setupError">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
      </div>

      <!-- Error actions -->
      <div class="actions" v-if="setupError">
        <button @click="retrySetup" class="btn-primary">Retry Setup</button>
        <button @click="openLogs" class="btn-secondary">View Full Logs</button>
      </div>

      <!-- Success actions -->
      <div class="actions" v-if="setupComplete">
        <button @click="startApp" class="btn-primary">Start Application</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'
import { listen } from '@tauri-apps/api/event'

const emit = defineEmits<{
  (e: 'setup-complete'): void
  (e: 'setup-error', message: string): void
}>()

interface Step { title: string; description: string; error: boolean }
interface LogEntry { message: string; level: 'info' | 'warning' | 'error' | 'success' }

// --- Setup steps (match setup_onnx_runtime.py) ---
const steps = ref<Step[]>([
  { title: 'Check Python', description: 'Verifying Python installation…', error: false },
  { title: 'Create Environment', description: 'Creating virtual environment…', error: false },
  { title: 'Install Packages', description: 'Installing onnxruntime, numpy, opencv…', error: false },
  { title: 'Verify Model', description: 'Checking model files…', error: false },
  { title: 'Smoke Test', description: 'Verifying all packages…', error: false },
  { title: 'Finalize', description: 'Saving configuration…', error: false },
])

const currentStep = ref(0)
const logs = ref<LogEntry[]>([])
const setupComplete = ref(false)
const setupError = ref(false)
const statusMessage = ref('Checking system…')
const logContainer = ref<HTMLElement | null>(null)
const setupStarted = ref(false)
const launchInProgress = ref(false)

// Pre-check state
const pythonPath = ref<string>('')
const depsInstalled = ref(false)
const modelDir = ref<string>('')
const runtimeDir = ref<string>('')

const progressPercent = computed(() =>
  Math.round((currentStep.value / steps.value.length) * 100)
)

const addLog = (message: string, level: LogEntry['level'] = 'info') => {
  logs.value.push({ message, level })
  nextTick(() => { if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight })
}

// ----- Environment pre-checks -----
const checkEnvironment = async () => {
  try {
    const py = await invoke<string>('check_python_installed')
    pythonPath.value = py
  } catch { pythonPath.value = '' }

  try {
    const ok = await invoke<boolean>('check_onnx_dependencies')
    depsInstalled.value = ok
  } catch { depsInstalled.value = false }

  try {
    const dir = await invoke<string>('check_model_available')
    modelDir.value = dir
  } catch { modelDir.value = '' }

  try {
    const dir = await invoke<string>('check_runtime_available')
    runtimeDir.value = dir
  } catch { runtimeDir.value = '' }
}

// ----- Run the lightweight ONNX setup -----
const runSetup = async () => {
  setupStarted.value = true
  statusMessage.value = 'Installing dependencies…'
  addLog('Starting PhenoAI setup…', 'info')

  // Register event listeners
  await listen('setup-progress', (event: any) => {
    const { step, message, level } = event.payload
    if (step !== undefined) currentStep.value = step
    if (message) { addLog(message, level || 'info'); statusMessage.value = message }
  })
  await listen('setup-complete', () => {
    setupComplete.value = true
    statusMessage.value = 'Setup complete! Ready to start.'
    addLog('✓ Setup completed successfully!', 'success')
  })
  await listen('setup-error', (event: any) => {
    const message = typeof event.payload === 'string'
      ? event.payload : (event.payload?.message || 'Unknown setup error')
    setupError.value = true
    steps.value[currentStep.value].error = true
    statusMessage.value = `Error: ${message}`
    addLog(`✗ ${message}`, 'error')
  })

  try {
    await invoke('run_first_time_setup')
  } catch (error) {
    setupError.value = true
    statusMessage.value = `Setup failed: ${error}`
    addLog(`Setup failed: ${error}`, 'error')
  }
}

// ----- Actions -----
const retrySetup = () => {
  setupError.value = false
  setupComplete.value = false
  setupStarted.value = false
  steps.value.forEach(s => s.error = false)
  currentStep.value = 0
  logs.value = []
  checkEnvironment()
}

const openLogs = async () => {
  try { await invoke('open_setup_logs') } catch (e) { console.error('Failed to open logs:', e) }
}

const startApp = async () => {
  try {
    launchInProgress.value = true
    setupError.value = false
    statusMessage.value = 'Starting backend…'
    addLog('Starting backend server…', 'info')

    const url = await invoke<string>('ensure_backend_running')
    addLog(`Backend is running at ${url}`, 'success')
    statusMessage.value = 'Backend started successfully.'

    emit('setup-complete')
  } catch (e) {
    console.error('Failed to start app:', e)
    setupError.value = true
    statusMessage.value = `Failed to start app: ${e}`
    addLog(`Failed to start app: ${e}`, 'error')
    emit('setup-error', `Failed to start app: ${e}`)
  } finally {
    launchInProgress.value = false
  }
}

onMounted(() => { checkEnvironment() })
</script>

<style scoped>
.setup-container {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
  overflow-y: auto;
  box-sizing: border-box;
}
.setup-card {
  background: #f8f9fa;
  border-radius: 16px;
  padding: 32px;
  max-width: 600px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0,0,0,.4);
  margin: auto;
  flex-shrink: 0;
}
.header { text-align: center; margin-bottom: 16px; }
.logo-icon { font-size: 36px; margin-bottom: 8px; }
.header h1 { color: #1a1a2e; font-size: 20px; margin: 0 0 6px; }
.subtitle { color: #666; font-size: 13px; margin: 0; }

/* Pre-check screen */
.choice-screen { padding: 20px 0; }
.choice-header { text-align: center; margin-bottom: 24px; }
.choice-header h2 { color: #1a1a2e; font-size: 24px; margin: 0 0 12px; }
.choice-header p { color: #666; font-size: 14px; margin: 0; }
.environment-check { background: #f0f0f0; border-radius: 8px; padding: 16px; margin-bottom: 24px; }
.check-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; font-size: 14px; color: #333; }
.check-item.success { color: #2e7d32; }
.check-item.warning { color: #f57c00; }
.check-icon { font-size: 18px; font-weight: bold; }

.all-ready, .needs-install, .needs-python, .needs-model { text-align: center; }
.ready-message { color: #2e7d32; font-weight: 600; font-size: 16px; margin-bottom: 16px; }
.info-message { color: #1565c0; font-size: 14px; margin-bottom: 16px; }

.help-text {
  background: #e3f2fd; border-left: 4px solid #2196f3;
  padding: 16px; border-radius: 4px;
}
.help-text p { margin: 0; font-size: 13px; color: #1565c0; line-height: 1.6; }

/* Steps */
.progress-section { margin-bottom: 16px; }
.steps-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px 16px; }
.step { display: flex; align-items: flex-start; padding: 8px 0; opacity: .5; transition: opacity .3s; }
.step.active, .step.completed { opacity: 1; }
.step.error { opacity: 1; }
.step-icon {
  width: 26px; height: 26px; border-radius: 50%; background: #ddd;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; color: #666; margin-right: 10px; flex-shrink: 0;
}
.step.completed .step-icon { background: #4caf50; color: #fff; }
.step.active .step-icon { background: #2196f3; color: #fff; }
.step.error .step-icon { background: #f44336; color: #fff; }
.spinner { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.step-content { flex: 1; }
.step-title { color: #1a1a2e; font-size: 15px; font-weight: 600; }
.step-description { color: #555; font-size: 13px; margin-top: 4px; }

/* Log */
.log-section { background: #1a1a2e; border-radius: 8px; margin-bottom: 20px; overflow: hidden; }
.log-header { padding: 10px 16px; background: #16213e; color: #ccc; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
.log-content { padding: 12px 16px; max-height: 150px; overflow-y: auto; font-family: 'Monaco','Menlo',monospace; font-size: 12px; }
.log-line { color: #ddd; padding: 2px 0; }
.log-line.warning { color: #ffc107; }
.log-line.error { color: #f44336; }
.log-line.success { color: #4caf50; }

/* Status bar */
.status-bar { margin-bottom: 20px; }
.status-text { color: #555; font-size: 14px; margin-bottom: 8px; }
.progress-bar { height: 4px; background: #ddd; border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #2196f3, #4caf50); transition: width .3s ease; }

/* Buttons */
.actions { display: flex; gap: 12px; justify-content: center; }
.btn-primary, .btn-secondary {
  padding: 12px 24px; border-radius: 8px; font-size: 14px;
  font-weight: 500; cursor: pointer; border: none; transition: all .2s;
}
.btn-primary { background: #2196f3; color: #fff; }
.btn-primary:hover { background: #1976d2; }
.btn-secondary { background: #333; color: #fff; }
.btn-secondary:hover { background: #444; }
</style>
