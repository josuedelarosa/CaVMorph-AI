<template>
  <div class="setup-container">
    <div class="setup-card">
      <div class="header">
        <div class="logo-icon">🐟</div>
        <h1>Fish Morphometrics</h1>
        <p class="subtitle">First-time Setup</p>
      </div>

      <!-- Choice Screen -->
      <div v-if="!setupStarted" class="choice-screen">
        <div class="choice-header">
          <h2>Environment Setup</h2>
          <p>This application requires a conda environment with PyTorch and mmpose.</p>
        </div>

        <div class="environment-check" v-if="condaPath">
          <div class="check-item success">
            <span class="check-icon">✓</span>
            <span>Conda found at: {{ condaPath }}</span>
          </div>
          <div class="check-item" :class="existingEnvClass" v-if="envCheckComplete">
            <span class="check-icon">{{ existingEnvIcon }}</span>
            <span>{{ existingEnvMessage }}</span>
          </div>
        </div>

        <div class="choices">
          <button 
            @click="useExistingEnv" 
            class="choice-btn"
            :disabled="!hasExistingEnv"
            :class="{ disabled: !hasExistingEnv }">
            <div class="choice-icon">🔗</div>
            <div class="choice-title">Use Existing Environment</div>
            <div class="choice-description">
              I already have cavfish310 installed<br>
              (following your manual setup instructions)
            </div>
          </button>

          <button @click="createNewEnv" class="choice-btn">
            <div class="choice-icon">🛠️</div>
            <div class="choice-title">Create New Environment</div>
            <div class="choice-description">
              Install PyTorch, mmpose, and all dependencies<br>
              (this will take 15-30 minutes)
            </div>
          </button>
        </div>

        <div class="help-text">
          <p><strong>Note:</strong> If you've already set up the cavfish310 environment using conda, 
          select "Use Existing Environment". Otherwise, choose "Create New Environment" to set everything up automatically.</p>
        </div>
      </div>

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

      <div v-if="setupStarted" class="log-section" v-show="logs.length > 0">
        <div class="log-header">Setup Log</div>
        <div class="log-content" ref="logContainer">
          <div v-for="(log, i) in logs" :key="i" :class="['log-line', log.level]">
            {{ log.message }}
          </div>
        </div>
      </div>

      <div v-if="setupStarted" class="status-bar">
        <div class="status-text">{{ statusMessage }}</div>
        <div class="progress-bar" v-if="!setupComplete && !setupError">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
      </div>

      <div class="actions" v-if="setupError">
        <button @click="retrySetup" class="btn-primary">Retry Setup</button>
        <button @click="openLogs" class="btn-secondary">View Full Logs</button>
      </div>

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

// Define emits
const emit = defineEmits<{
  (e: 'setup-complete'): void
  (e: 'setup-error', message: string): void
}>()

interface Step {
  title: string
  description: string
  error: boolean
}

interface LogEntry {
  message: string
  level: 'info' | 'warning' | 'error' | 'success'
}

const steps = ref<Step[]>([
  { title: 'Checking System', description: 'Verifying conda installation...', error: false },
  { title: 'Creating Environment', description: 'Setting up Python 3.10 environment...', error: false },
  { title: 'Installing PyTorch', description: 'Installing PyTorch for your system...', error: false },
  { title: 'Installing MM Packages', description: 'Installing mmpose, mmengine, mmcv...', error: false },
  { title: 'Installing Dependencies', description: 'Installing FastAPI and other packages...', error: false },
  { title: 'Downloading Model', description: 'Downloading model weights (~1GB)...', error: false },
  { title: 'Finalizing', description: 'Verifying installation...', error: false },
])

const currentStep = ref(0)
const logs = ref<LogEntry[]>([])
const setupComplete = ref(false)
const setupError = ref(false)
const statusMessage = ref('Initializing setup...')
const logContainer = ref<HTMLElement | null>(null)
const setupStarted = ref(false)
const condaPath = ref<string>('')
const hasExistingEnv = ref(false)
const envCheckComplete = ref(false)

const progressPercent = computed(() => {
  return Math.round((currentStep.value / steps.value.length) * 100)
})

const existingEnvClass = computed(() => {
  return hasExistingEnv.value ? 'success' : 'warning'
})

const existingEnvIcon = computed(() => {
  return hasExistingEnv.value ? '✓' : '⚠'
})

const existingEnvMessage = computed(() => {
  return hasExistingEnv.value 
    ? 'cavfish310 environment found and ready'
    : 'cavfish310 environment not found or incomplete'
})

const addLog = (message: string, level: LogEntry['level'] = 'info') => {
  logs.value.push({ message, level })
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

const checkEnvironment = async () => {
  try {
    // First check if Command Line Tools are installed (macOS only)
    try {
      const toolsInstalled = await invoke<boolean>('check_xcode_tools_installed')
      if (!toolsInstalled) {
        addLog('⚠️ macOS Command Line Developer Tools are not installed', 'error')
        addLog('', 'error')
        addLog('Please install them by running in Terminal:', 'error')
        addLog('  xcode-select --install', 'error')
        addLog('', 'error')
        addLog('Or click "Install" when the system dialog appears.', 'error')
        addLog('Then restart this application.', 'error')
        setupError.value = true
        statusMessage.value = 'Command Line Developer Tools required'
        return
      }
    } catch (err) {
      console.log('Xcode tools check not applicable or failed:', err)
    }
    
    // Check if conda is installed
    const conda = await invoke<string>('check_conda_installed')
    condaPath.value = conda
    
    // Check if cavfish310 exists
    const envExists = await invoke<boolean>('check_conda_env_exists')
    hasExistingEnv.value = envExists
    envCheckComplete.value = true
  } catch (error) {
    console.error('Environment check failed:', error)
    condaPath.value = ''
    hasExistingEnv.value = false
    envCheckComplete.value = true
  }
}

const useExistingEnv = async () => {
  setupStarted.value = true
  statusMessage.value = 'Verifying existing environment...'
  addLog('Checking if existing cavfish310 environment has all required packages', 'info')
  
  try {
    // First verify that the environment is actually complete
    const isComplete = await invoke('check_if_setup_needed')
    
    if (isComplete === false) {
      // Environment exists and is complete
      statusMessage.value = 'Starting backend with existing environment...'
      addLog('✓ Environment is complete, starting backend', 'success')
      
      await invoke('finish_setup_and_start')
      setupComplete.value = true
      statusMessage.value = 'Backend started successfully!'
      addLog('✓ Backend started successfully!', 'success')
      emit('setup-complete')
    } else {
      // Environment exists but is incomplete - force reinstall
      statusMessage.value = 'Environment incomplete, running full setup...'
      addLog('⚠ Environment exists but packages are missing or incomplete', 'warning')
      addLog('Starting full installation process...', 'info')
      
      // Switch to full setup mode
      setupStarted.value = false
      hasExistingEnv.value = false
      
      // Auto-start the full setup
      setTimeout(() => createNewEnv(), 500)
    }
  } catch (error) {
    setupError.value = true
    statusMessage.value = `Failed to verify environment: ${error}`
    addLog(`✗ Failed to verify environment: ${error}`, 'error')
    emit('setup-error', `${error}`)
  }
}

const createNewEnv = () => {
  setupStarted.value = true
  startSetup()
}

const startSetup = async () => {
  try {
    // Listen for setup progress events from Rust backend
    await listen('setup-progress', (event: any) => {
      const { step, message, level } = event.payload
      if (step !== undefined) {
        currentStep.value = step
      }
      if (message) {
        addLog(message, level || 'info')
        statusMessage.value = message
      }
    })

    await listen('setup-complete', () => {
      setupComplete.value = true
      statusMessage.value = 'Setup complete! Ready to start.'
      addLog('✓ Setup completed successfully!', 'success')
    })

    await listen('setup-error', (event: any) => {
      setupError.value = true
      steps.value[currentStep.value].error = true
      statusMessage.value = `Error: ${event.payload.message}`
      addLog(`✗ ${event.payload.message}`, 'error')
    })

    // Start the setup process
    addLog('Starting MorphologIA setup...', 'info')
    await invoke('run_first_time_setup')
  } catch (error) {
    setupError.value = true
    statusMessage.value = `Setup failed: ${error}`
    addLog(`Setup failed: ${error}`, 'error')
  }
}

const retrySetup = () => {
  setupError.value = false
  steps.value.forEach(s => s.error = false)
  currentStep.value = 0
  logs.value = []
  startSetup()
}

const openLogs = async () => {
  try {
    await invoke('open_setup_logs')
  } catch (e) {
    console.error('Failed to open logs:', e)
  }
}

const startApp = async () => {
  try {
    statusMessage.value = 'Starting backend...'
    addLog('Starting backend server...', 'info')
    await invoke('finish_setup_and_start')
    addLog('Backend started successfully!', 'success')
    // Notify parent that setup is complete
    emit('setup-complete')
  } catch (e) {
    console.error('Failed to start app:', e)
    addLog(`Failed to start app: ${e}`, 'error')
    emit('setup-error', `Failed to start app: ${e}`)
  }
}

onMounted(() => {
  checkEnvironment()
})
</script>

<style scoped>
.setup-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
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
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  margin: auto;
  flex-shrink: 0;
}

.header {
  text-align: center;
  margin-bottom: 16px;
}

.logo-icon {
  font-size: 36px;
  margin-bottom: 8px;
}

.header h1 {
  color: #1a1a2e;
  font-size: 20px;
  margin: 0 0 6px 0;
}

.subtitle {
  color: #666;
  font-size: 13px;
  margin: 0;
}

.progress-section {
  margin-bottom: 16px;
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
}

.step {
  display: flex;
  align-items: flex-start;
  padding: 8px 0;
  opacity: 0.5;
  transition: opacity 0.3s;
}

.step.active, .step.completed {
  opacity: 1;
}

.step.error {
  opacity: 1;
}

.step-icon {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #666;
  margin-right: 10px;
  flex-shrink: 0;
}

.step.completed .step-icon {
  background: #4caf50;
  color: #fff;
}

.step.active .step-icon {
  background: #2196f3;
  color: #fff;
}

.step.error .step-icon {
  background: #f44336;
  color: #fff;
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.step-content {
  flex: 1;
}

.step-title {
  color: #1a1a2e;
  font-size: 15px;
  font-weight: 600;
}

.step-description {
  color: #555;
  font-size: 13px;
  margin-top: 4px;
}

.log-section {
  background: #1a1a2e;
  border-radius: 8px;
  margin-bottom: 20px;
  overflow: hidden;
}

.log-header {
  padding: 10px 16px;
  background: #16213e;
  color: #ccc;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.log-content {
  padding: 12px 16px;
  max-height: 150px;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.log-line {
  color: #ddd;
  padding: 2px 0;
}

.log-line.warning { color: #ffc107; }
.log-line.error { color: #f44336; }
.log-line.success { color: #4caf50; }

.status-bar {
  margin-bottom: 20px;
}

.status-text {
  color: #555;
  font-size: 14px;
  margin-bottom: 8px;
}

.progress-bar {
  height: 4px;
  background: #ddd;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #2196f3, #4caf50);
  transition: width 0.3s ease;
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-primary, .btn-secondary {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: #2196f3;
  color: #fff;
}

.btn-primary:hover {
  background: #1976d2;
}

.btn-secondary {
  background: #333;
  color: #fff;
}

.btn-secondary:hover {
  background: #444;
}

/* Choice Screen Styles */
.choice-screen {
  padding: 20px 0;
}

.choice-header {
  text-align: center;
  margin-bottom: 24px;
}

.choice-header h2 {
  color: #1a1a2e;
  font-size: 24px;
  margin: 0 0 12px 0;
}

.choice-header p {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.environment-check {
  background: #f0f0f0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  font-size: 14px;
  color: #333;
}

.check-item.success {
  color: #2e7d32;
}

.check-item.warning {
  color: #f57c00;
}

.check-icon {
  font-size: 18px;
  font-weight: bold;
}

.choices {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.choice-btn {
  background: white;
  border: 2px solid #ddd;
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.choice-btn:hover:not(.disabled) {
  border-color: #2196f3;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(33, 150, 243, 0.2);
}

.choice-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.choice-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.choice-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.choice-description {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

.help-text {
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
  padding: 16px;
  border-radius: 4px;
}

.help-text p {
  margin: 0;
  font-size: 13px;
  color: #1565c0;
  line-height: 1.6;
}

.help-text strong {
  font-weight: 600;
}
</style>
