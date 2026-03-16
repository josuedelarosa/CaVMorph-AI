<template>
  <div v-if="show" class="welcome-overlay" @click.self="handleClose">
    <div class="welcome-modal">
      <button class="close-btn" @click="handleClose">&times;</button>
      
      <div class="welcome-header">
        <h1>PhenoAI</h1>
        <p class="subtitle">Phenotype analysis for fish morphometrics</p>
      </div>

      <div class="guide-content">
        <div class="guide-section">
          <h2>Supported Formats</h2>
          <p>PhenoAI accepts the following image formats:</p>
          <ul>
            <li><strong>JPEG</strong> (.jpg, .jpeg)</li>
            <li><strong>PNG</strong> (.png)</li>
            <li><strong>BMP</strong> (.bmp)</li>
            <li><strong>TIFF</strong> (.tif, .tiff)</li>
          </ul>
          <p class="tip">For best results, use high-resolution images with clear specimens.</p>
        </div>

        <div class="guide-section">
          <h2>Profiles</h2>
          <p><strong>Profiles</strong> group specimens by species or experiment type.</p>
          <div class="explanation-box">
            <p><strong>Each profile can have its own keypoint configuration.</strong></p>
            <ul>
              <li>The default profile uses 20 anatomical keypoints</li>
              <li>Create custom profiles for specific species</li>
              <li>Organize data by experiment, location, or population</li>
            </ul>
          </div>
        </div>

        <div class="guide-section">
          <h2>Workflow</h2>
          <ol class="quick-start-list">
            <li>Select or create a <strong>Profile</strong> for your specimen type</li>
            <li>Select a folder of images</li>
            <li>Click <strong>Run Analysis</strong> to detect keypoints</li>
            <li>Review results and measurements</li>
            <li>Export annotated data</li>
          </ol>
        </div>

        <div class="guide-section">
          <h2>Export</h2>
          <p>Results are saved to:</p>
          <div class="path-box">
            <code>~/Documents/PhenoAI/</code>
          </div>
          <p>Each export includes annotated images, phenotype measurements, and profile metadata.</p>
        </div>
      </div>

      <div class="welcome-footer">
        <label class="checkbox-label">
          <input type="checkbox" v-model="dontShowAgain" />
          <span>Don't show again</span>
        </label>
        <button class="start-btn" @click="handleClose">Start</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const dontShowAgain = ref(false)

const handleClose = () => {
  if (dontShowAgain.value) {
    localStorage.setItem('phenoai-welcome-shown', 'true')
  }
  emit('close')
}
</script>

<style scoped>
.welcome-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
  backdrop-filter: blur(3px);
}

.welcome-modal {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  max-width: 640px;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: var(--shadow-overlay);
  position: relative;
  animation: fadeIn 0.15s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  background: transparent;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: color 0.12s, background 0.12s;
  z-index: 10;
}

.close-btn:hover {
  color: var(--text-primary);
  background: var(--bg-overlay);
}

.welcome-header {
  text-align: center;
  padding: var(--sp-32) var(--sp-32) var(--sp-16);
}

.welcome-header h1 {
  margin: 0 0 6px 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.subtitle {
  margin: 0;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}

.guide-content {
  padding: var(--sp-16) var(--sp-32);
}

.guide-section {
  margin-bottom: var(--sp-24);
}

.guide-section:last-child {
  margin-bottom: 0;
}

.guide-section h2 {
  color: var(--text-primary);
  font-size: var(--fs-md);
  margin: 0 0 var(--sp-8) 0;
  font-weight: 600;
}

.guide-section p {
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 var(--sp-8) 0;
  font-size: var(--fs-sm);
}

.guide-section ul,
.guide-section ol {
  color: var(--text-secondary);
  line-height: 1.7;
  margin: var(--sp-8) 0;
  padding-left: 20px;
  font-size: var(--fs-sm);
}

.guide-section li {
  margin-bottom: 4px;
}

.guide-section strong {
  color: var(--text-primary);
  font-weight: 600;
}

.tip {
  background: rgba(88, 166, 255, 0.08);
  border-left: 3px solid var(--accent-blue);
  padding: var(--sp-8) var(--sp-12);
  border-radius: var(--radius-sm);
  font-size: var(--fs-xs) !important;
  color: var(--accent-blue) !important;
}

.explanation-box {
  background: var(--bg-canvas);
  border: 1px solid var(--border-muted);
  border-radius: var(--radius-md);
  padding: var(--sp-12);
  margin: var(--sp-8) 0;
}

.explanation-box p {
  margin: 0 0 var(--sp-4) 0;
}

.explanation-box ul {
  margin: var(--sp-4) 0 0 0;
}

.path-box {
  background: var(--bg-canvas);
  border: 1px solid var(--border-muted);
  color: var(--accent-green);
  padding: var(--sp-8) var(--sp-12);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  margin: var(--sp-8) 0;
}

.path-box code {
  font-size: var(--fs-sm);
}

.quick-start-list {
  padding-left: 20px;
}

.quick-start-list li {
  margin-bottom: var(--sp-8);
}

.welcome-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-16) var(--sp-32);
  border-top: 1px solid var(--border-default);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--sp-8);
  cursor: pointer;
  user-select: none;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}

.checkbox-label input[type="checkbox"] {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: var(--accent-blue);
}

.start-btn {
  background: var(--accent-blue);
  color: var(--text-on-emphasis);
  border: none;
  padding: 6px 20px;
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-weight: 500;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: background 0.12s;
}

.start-btn:hover {
  background: #4c9aed;
}

.welcome-modal::-webkit-scrollbar { width: 6px; }
.welcome-modal::-webkit-scrollbar-track { background: transparent; }
.welcome-modal::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: 3px; }
.welcome-modal::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
</style>
