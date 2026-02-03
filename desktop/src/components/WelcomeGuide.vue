<template>
  <div v-if="show" class="welcome-overlay" @click.self="handleClose">
    <div class="welcome-modal">
      <button class="close-btn" @click="handleClose">✕</button>
      
      <div class="welcome-header">
        <div class="logo">🐟</div>
        <h1>Welcome to PhenoAI</h1>
        <p class="subtitle">AI-powered phenotype analysis for fish morphometrics</p>
      </div>

      <div class="guide-content">
        <div class="guide-section">
          <div class="section-icon">📂</div>
          <h2>Supported Formats</h2>
          <p>PhenoAI accepts the following image formats:</p>
          <ul>
            <li><strong>JPEG</strong> (.jpg, .jpeg) - Recommended</li>
            <li><strong>PNG</strong> (.png) - Lossless quality</li>
            <li><strong>BMP</strong> (.bmp) - Uncompressed</li>
            <li><strong>TIFF</strong> (.tif, .tiff) - High quality</li>
          </ul>
          <p class="tip">💡 For best results, use high-resolution images with clear fish specimens</p>
        </div>

        <div class="guide-section">
          <div class="section-icon">🏷️</div>
          <h2>Understanding Profiles</h2>
          <p><strong>Profiles</strong> are like <em>species classes</em> or <em>fish types</em> in your analysis.</p>
          <div class="explanation-box">
            <p><strong>What they do:</strong></p>
            <ul>
              <li>Group similar fish specimens together</li>
              <li>Each profile can have its own keypoint configuration</li>
              <li>Default profile uses 20 anatomical keypoints</li>
            </ul>
            <p><strong>Why use multiple profiles?</strong></p>
            <ul>
              <li>Different fish species have different body structures</li>
              <li>Keypoint detection accuracy improves with species-specific models</li>
              <li>Organize your data by experiment, location, or population</li>
            </ul>
          </div>
          <p class="note">
            <strong>Note:</strong> The default 20-keypoint annotation is a general model. 
            For precise biological analysis, create custom profiles for your specific species.
          </p>
        </div>

        <div class="guide-section">
          <div class="section-icon">🎯</div>
          <h2>Quick Start</h2>
          <ol class="quick-start-list">
            <li>Select or create a <strong>Profile</strong> for your fish type</li>
            <li>Drag & drop images or click <strong>Upload Images</strong></li>
            <li>Click <strong>Analyze</strong> to detect keypoints automatically</li>
            <li>Review and adjust keypoints if needed</li>
            <li>Export your annotated data as JPEG with overlays</li>
          </ol>
        </div>

        <div class="guide-section">
          <div class="section-icon">📊</div>
          <h2>Export & Results</h2>
          <p>Analyzed images are automatically saved to:</p>
          <div class="path-box">
            <code>~/Documents/PhenoAI/</code>
          </div>
          <p>Each export includes:</p>
          <ul>
            <li>Annotated image with keypoint overlays</li>
            <li>Phenotype measurements (distances, ratios)</li>
            <li>Timestamp and profile information</li>
          </ul>
        </div>
      </div>

      <div class="welcome-footer">
        <label class="checkbox-label">
          <input type="checkbox" v-model="dontShowAgain" />
          <span>Don't show this again</span>
        </label>
        <button class="start-btn" @click="handleClose">Get Started</button>
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
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.welcome-modal {
  background: white;
  border-radius: 16px;
  max-width: 700px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: #f5f5f5;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 10;
}

.close-btn:hover {
  background: #e0e0e0;
  transform: rotate(90deg);
}

.welcome-header {
  text-align: center;
  padding: 40px 40px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 16px 16px 0 0;
}

.logo {
  font-size: 64px;
  margin-bottom: 16px;
}

.welcome-header h1 {
  margin: 0 0 8px 0;
  font-size: 32px;
  font-weight: 700;
}

.subtitle {
  margin: 0;
  font-size: 16px;
  opacity: 0.95;
}

.guide-content {
  padding: 32px 40px;
}

.guide-section {
  margin-bottom: 32px;
}

.guide-section:last-child {
  margin-bottom: 0;
}

.section-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.guide-section h2 {
  color: #1a1a2e;
  font-size: 20px;
  margin: 0 0 12px 0;
  font-weight: 600;
}

.guide-section p {
  color: #555;
  line-height: 1.6;
  margin: 0 0 12px 0;
}

.guide-section ul,
.guide-section ol {
  color: #555;
  line-height: 1.8;
  margin: 12px 0;
  padding-left: 24px;
}

.guide-section li {
  margin-bottom: 8px;
}

.guide-section strong {
  color: #333;
  font-weight: 600;
}

.guide-section em {
  color: #667eea;
  font-style: italic;
}

.tip {
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
  color: #1565c0 !important;
  margin-top: 12px !important;
}

.note {
  background: #fff3e0;
  border-left: 4px solid #ff9800;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
  color: #e65100 !important;
  margin-top: 12px !important;
}

.explanation-box {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
  margin: 12px 0;
}

.explanation-box p {
  margin: 0 0 8px 0;
  font-weight: 600;
}

.explanation-box ul {
  margin: 8px 0 0 0;
}

.path-box {
  background: #2d2d2d;
  color: #a8e063;
  padding: 12px;
  border-radius: 6px;
  font-family: 'Monaco', 'Courier New', monospace;
  margin: 12px 0;
}

.path-box code {
  font-size: 14px;
}

.quick-start-list {
  counter-reset: step-counter;
  list-style: none;
  padding-left: 0;
}

.quick-start-list li {
  counter-increment: step-counter;
  position: relative;
  padding-left: 40px;
  margin-bottom: 16px;
}

.quick-start-list li::before {
  content: counter(step-counter);
  position: absolute;
  left: 0;
  top: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
}

.welcome-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 40px;
  border-top: 1px solid #e0e0e0;
  background: #fafafa;
  border-radius: 0 0 16px 16px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  color: #666;
  font-size: 14px;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.start-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 32px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

.start-btn:active {
  transform: translateY(0);
}

/* Scrollbar styling */
.welcome-modal::-webkit-scrollbar {
  width: 8px;
}

.welcome-modal::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.welcome-modal::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.welcome-modal::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
