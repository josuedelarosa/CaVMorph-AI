<template>
  <div class="setup-container">
    <div class="setup-card">
      <div class="header">
        <h1>PhenoAI</h1>
        <p class="subtitle">First-time Setup</p>
      </div>

      <!-- Pre-setup: system check summary -->
      <div v-if="!setupStarted && !setupComplete" class="choice-screen">
        <div class="choice-header">
          <h2>Environment Check</h2>
          <p>Verifying Python runtime and model files.</p>
        </div>

        <div class="environment-check">
          <div class="check-item" :class="pythonPath ? 'success' : 'warning'">
            <span class="check-icon">{{ pythonPath ? '\u2713' : '\u2717' }}</span>
            <span v-if="pythonPath">Python found: {{ pythonPath }}</span>
            <span v-else>Python runtime not found</span>
          </div>
          <div class="check-item" :class="depsInstalled ? 'success' : 'warning'" v-if="pythonPath">
            <span class="check-icon">{{ depsInstalled ? '\u2713' : '\u2013' }}</span>
            <span v-if="depsInstalled">ONNX runtime packages installed</span>
            <span v-else>ONNX runtime packages need to be installed</span>
          </div>
          <div class="check-item" :class="modelDir ? 'success' : 'warning'">
            <span class="check-icon">{{ modelDir ? '\u2713' : '\u2013' }}</span>
            <span v-if="modelDir">Model files found</span>
            <span v-else>Model files not found</span>
          </div>
          <div class="check-item" :class="runtimeDir ? 'success' : 'warning'">
            <span class="check-icon">{{ runtimeDir ? '\u2713' : '\u2013' }}</span>
            <span v-if="runtimeDir">Inference runtime found</span>
            <span v-else>Inference runtime files missing</span>
          </div>
        </div>

        <div v-if="pythonPath && depsInstalled && modelDir && runtimeDir" class="all-ready">
          <p class="ready-message">All checks passed.</p>
          <button @click="startApp" class="btn-primary" :disabled="launchInProgress">
            {{ launchInProgress ? 'Starting\u2026' : 'Start Application' }}
          </button>
        </div>

        <div v-else-if="pythonPath && modelDir && runtimeDir" class="needs-install">
          <p class="info-message">Some dependencies need to be installed.</p>
          <button @click="runSetup" class="btn-primary">Install Dependencies</button>
        </div>

        <div v-else-if="pythonPath && modelDir && !runtimeDir" class="needs-model">
          <div class="help-text">
            <p><strong>Inference runtime files are missing.</strong>
              Reinstall PhenoAI using the latest installer, then click Check Again.</p>
          </div>
          <div class="actions" style="margin-top:12px">
            <button @click="checkEnvironment" class="btn-secondary">Check Again</button>
            <button @click="openLogs" class="btn-secondary">View Logs</button>
          </div>
        </div>

        <div v-else-if="!pythonPath" class="needs-python">
          <div class="help-text">
            <p><strong>No Python runtime found.</strong>
              Install Python 3.9+ or reinstall PhenoAI with the bundled runtime.</p>
          </div>
          <div class="actions" style="margin-top:12px">
            <button @click="checkEnvironment" class="btn-secondary">Check Again</button>
          </div>
        </div>

        <div v-else-if="!modelDir" class="needs-model">
          <div class="help-text">
            <p><strong>Model files not found.</strong>
              Place model.onnx and model_metadata.json in the models directory, then click Check Again.</p>
          </div>
          <div class="actions" style="margin-top:12px">
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
              <span v-if="currentStep > index && !step.error">\u2713</span>
              <span v-else-if="step.error">\u2717</span>
              <span v-else-if="currentStep === index" class="spinner-dot"></span>
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
          <div v-if="launchInProgress && logs.length === 0" class="log-line">Starting backend...</div>
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
        <button @click="retrySetup" class="btn-primary">Retry</button>
        <button @click="openLogs" class="btn-secondary">View Logs</button>
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
import { isTauri, tauriInvoke, tauriListen } from '../utils/platform'

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
  if (!isTauri) {
    // Web mode — skip environment checks, backend is pre-configured
    pythonPath.value = 'web-mode'
    depsInstalled.value = true
    modelDir.value = 'web-mode'
    runtimeDir.value = 'web-mode'
    return
  }

  try {
    const py = await tauriInvoke<string>('check_python_installed')
    pythonPath.value = py
  } catch { pythonPath.value = '' }

  try {
    const ok = await tauriInvoke<boolean>('check_onnx_dependencies')
    depsInstalled.value = ok
  } catch { depsInstalled.value = false }

  try {
    const dir = await tauriInvoke<string>('check_model_available')
    modelDir.value = dir
  } catch { modelDir.value = '' }

  try {
    const dir = await tauriInvoke<string>('check_runtime_available')
    runtimeDir.value = dir
  } catch { runtimeDir.value = '' }
}

// ----- Run the lightweight ONNX setup -----
const runSetup = async () => {
  setupStarted.value = true
  statusMessage.value = 'Installing dependencies…'
  addLog('Starting PhenoAI setup…', 'info')

  // Register event listeners
  await tauriListen('setup-progress', (payload: any) => {
    const { step, message, level } = payload
    if (step !== undefined) currentStep.value = step
    if (message) { addLog(message, level || 'info'); statusMessage.value = message }
  })
  await tauriListen('setup-complete', () => {
    setupComplete.value = true
    statusMessage.value = 'Setup complete! Ready to start.'
    addLog('✓ Setup completed successfully!', 'success')
  })
  await tauriListen('setup-error', (payload: any) => {
    const message = typeof payload === 'string'
      ? payload : (payload?.message || 'Unknown setup error')
    setupError.value = true
    steps.value[currentStep.value].error = true
    statusMessage.value = `Error: ${message}`
    addLog(`✗ ${message}`, 'error')
  })

  try {
    await tauriInvoke('run_first_time_setup')
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
  try { await tauriInvoke('open_setup_logs') } catch (e) { console.error('Failed to open logs:', e) }
}

const startApp = async () => {
  try {
    launchInProgress.value = true
    setupError.value = false
    statusMessage.value = 'Starting backend…'
    addLog('Starting backend server…', 'info')

    const url = await tauriInvoke<string>('ensure_backend_running')
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
  background: var(--bg-canvas, #0d1117);
  padding: 20px;
  overflow-y: auto;
  box-sizing: border-box;
}
.setup-card {
  background: var(--bg-surface, #161b22);
  border: 1px solid var(--border-default, #30363d);
  border-radius: 8px;
  padding: 28px;
  max-width: 560px;
  width: 100%;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  margin: auto;
  flex-shrink: 0;
}
.header { text-align: center; margin-bottom: 16px; }
.header h1 { color: var(--text-primary, #c9d1d9); font-size: 18px; font-weight: 600; margin: 0 0 4px; }
.subtitle { color: var(--text-secondary, #8b949e); font-size: 12px; margin: 0; }

.choice-screen { padding: 16px 0; }
.choice-header { text-align: center; margin-bottom: 20px; }
.choice-header h2 { color: var(--text-primary, #c9d1d9); font-size: 16px; font-weight: 600; margin: 0 0 8px; }
.choice-header p { color: var(--text-secondary, #8b949e); font-size: 13px; margin: 0; }

.environment-check {
  background: var(--bg-canvas, #0d1117);
  border: 1px solid var(--border-default, #30363d);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 20px;
}
.check-item {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 0; font-size: 13px; color: var(--text-secondary, #8b949e);
}
.check-item.success { color: var(--accent-green, #3fb950); }
.check-item.warning { color: var(--accent-orange, #d29922); }
.check-icon { font-size: 14px; font-weight: 700; width: 16px; text-align: center; flex-shrink: 0; }

.all-ready, .needs-install, .needs-python, .needs-model { text-align: center; }
.ready-message { color: var(--accent-green, #3fb950); font-weight: 600; font-size: 14px; margin-bottom: 12px; }
.info-message { color: var(--accent-blue, #58a6ff); font-size: 13px; margin-bottom: 12px; }

.help-text {
  background: rgba(88, 166, 255, 0.08);
  border-left: 3px solid var(--accent-blue, #58a6ff);
  padding: 12px; border-radius: 4px;
}
.help-text p { margin: 0; font-size: 12px; color: var(--text-secondary, #8b949e); line-height: 1.6; }
.help-text strong { color: var(--text-primary, #c9d1d9); }

.progress-section { margin-bottom: 16px; }
.steps-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 6px 12px; }
.step { display: flex; align-items: flex-start; padding: 6px 0; opacity: .4; transition: opacity .2s; }
.step.active, .step.completed { opacity: 1; }
.step.error { opacity: 1; }
.step-icon {
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--bg-overlay, #21262d);
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; color: var(--text-muted, #484f58);
  margin-right: 8px; flex-shrink: 0;
}
.step.completed .step-icon { background: var(--accent-green, #3fb950); color: #fff; }
.step.active .step-icon { background: var(--accent-blue, #58a6ff); color: #fff; }
.step.error .step-icon { background: var(--accent-red, #f85149); color: #fff; }

.spinner-dot {
  width: 8px; height: 8px; border: 2px solid transparent;
  border-top-color: #fff; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.step-content { flex: 1; }
.step-title { color: var(--text-primary, #c9d1d9); font-size: 13px; font-weight: 600; }
.step-description { color: var(--text-secondary, #8b949e); font-size: 12px; margin-top: 2px; }

.log-section {
  background: var(--bg-canvas, #0d1117);
  border: 1px solid var(--border-default, #30363d);
  border-radius: 6px; margin-bottom: 16px; overflow: hidden;
}
.log-header {
  padding: 6px 12px; background: var(--bg-overlay, #21262d);
  color: var(--text-muted, #484f58); font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;
}
.log-content {
  padding: 8px 12px; max-height: 140px; overflow-y: auto;
  font-family: var(--font-mono, monospace); font-size: 11px;
}
.log-line { color: var(--text-secondary, #8b949e); padding: 1px 0; }
.log-line.warning { color: var(--accent-orange, #d29922); }
.log-line.error { color: var(--accent-red, #f85149); }
.log-line.success { color: var(--accent-green, #3fb950); }

.status-bar { margin-bottom: 16px; }
.status-text { color: var(--text-secondary, #8b949e); font-size: 13px; margin-bottom: 6px; }
.progress-bar { height: 3px; background: var(--bg-overlay, #21262d); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--accent-blue, #58a6ff); transition: width .3s ease; }

.actions { display: flex; gap: 8px; justify-content: center; }
.btn-primary, .btn-secondary {
  padding: 6px 16px; border-radius: 6px; font-size: 13px;
  font-weight: 500; cursor: pointer; border: 1px solid transparent;
  transition: background .12s; font-family: var(--font-sans, sans-serif);
}
.btn-primary { background: var(--accent-blue, #58a6ff); color: #fff; }
.btn-primary:hover { background: #4c9aed; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  background: var(--bg-overlay, #21262d); color: var(--text-primary, #c9d1d9);
  border-color: var(--border-default, #30363d);
}
.btn-secondary:hover { background: var(--bg-surface-raised, #1c2129); }
</style>
