<template>
  <div v-if="show" class="welcome-overlay" @click.self="handleClose">
    <div class="welcome-modal">
      <button class="close-btn" @click="handleClose">&times;</button>

      <!-- Two-column body -->
      <div class="welcome-body">

        <!-- Left column: brand + workflow + export -->
        <div class="welcome-col welcome-col-left">
          <div class="welcome-brand">
            <svg class="brand-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <ellipse cx="12" cy="12" rx="9" ry="5.5"/>
              <circle cx="8.5" cy="12" r="1.5" fill="currentColor" stroke="none"/>
              <path d="M21 12c-2-3-5-5.5-9-5.5" stroke-dasharray="2.5 1.5" stroke-linecap="round"/>
            </svg>
            <h1>Fishometrics</h1>
            <p class="subtitle">Phenotype analysis for fish morphometrics</p>
          </div>

          <div class="col-section">
            <h2>Workflow</h2>
            <ol class="workflow-list">
              <li>Select or create a <strong>Profile</strong> for your specimen type</li>
              <li>Click <strong>Browse</strong> to choose a folder of images</li>
              <li>Click <strong>Run Analysis</strong> to detect keypoints</li>
              <li>Review results and measurements in the table</li>
              <li>Export annotated images and phenotype data</li>
            </ol>
          </div>

          <div class="col-section">
            <h2>Export</h2>
            <p>Results are saved to:</p>
            <div class="path-box"><code>~/Documents/Fishometrics/</code></div>
            <p>Each export includes annotated images, phenotype measurements, and profile metadata.</p>
          </div>

          <div class="col-section">
            <h2>About</h2>
            <p>Based on the paper:</p>
            <button class="paper-link" @click="openLink('https://doi.org/10.1038/s41597-025-04868-0')">
              Morphological trait database for Neotropical freshwater fishes powered from artificial intelligence
            </button>
            <p class="paper-authors">Poveda-Cuellar, J.L.; Rodríguez-de la Rosa, J.; Martínez-Carrillo, F.; García-Melo, J.E.; García-Melo, L.J.; Marchant, S. &amp; Reu, B.</p>
          </div>
        </div>

        <!-- Divider -->
        <div class="col-divider"></div>

        <!-- Right column: formats + profiles -->
        <div class="welcome-col welcome-col-right">
          <div class="col-section">
            <h2>Supported Formats</h2>
            <p>Fishometrics accepts the following image formats:</p>
            <ul class="format-list">
              <li><span class="fmt-badge">JPEG</span>&nbsp;.jpg, .jpeg</li>
              <li><span class="fmt-badge">PNG</span>&nbsp;.png</li>
              <li><span class="fmt-badge">BMP</span>&nbsp;.bmp</li>
              <li><span class="fmt-badge">TIFF</span>&nbsp;.tif, .tiff</li>
            </ul>
            <p class="tip">For best results, use high-resolution images with clear specimens.</p>
          </div>

          <div class="col-section">
            <h2>Profiles</h2>
            <p><strong>Profiles</strong> group specimens by species or experiment type.</p>
            <div class="info-box">
              <ul>
                <li>Each profile has its own keypoint configuration</li>
                <li>The default profile uses 20 anatomical keypoints</li>
                <li>Create custom profiles for specific species</li>
                <li>Organize data by experiment, location, or population</li>
              </ul>
            </div>
          </div>

          <div class="col-section">
            <h2>Learn More</h2>
            <p>For documentation, source code, and issue tracking, visit the <a href="https://github.com/josuedelarosa/CaVMorph-AI" target="_blank">project repository</a>.</p>
          </div>
        </div>

      </div><!-- /.welcome-body -->

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
import { openExternal } from '../utils/platform'

function openLink(url: string) {
  openExternal(url)
}

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const dontShowAgain = ref(false)

const handleClose = () => {
  if (dontShowAgain.value) {
    localStorage.setItem('fishometrics-welcome-shown', 'true')
  }
  emit('close')
}
</script>

<style scoped>
/* ── Overlay ──────────────────────────────────────────────── */
.welcome-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 24px;
  backdrop-filter: blur(3px);
}

/* ── Modal shell ──────────────────────────────────────────── */
.welcome-modal {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  width: 820px;
  max-width: 96vw;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-overlay);
  position: relative;
  animation: fadeIn 0.15s ease-out;
  overflow: hidden;            /* prevent any child scrolling */
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Close button ─────────────────────────────────────────── */
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
  background: var(--bg-canvas);
}

/* ── 2-column body ────────────────────────────────────────── */
.welcome-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.welcome-col {
  flex: 1;
  padding: 28px 28px 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.col-divider {
  width: 1px;
  background: var(--border-muted);
  margin: 20px 0;
}

/* ── Brand block ──────────────────────────────────────────── */
.welcome-brand {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.brand-svg {
  width: 28px;
  height: 28px;
  color: var(--accent-blue);
  margin-bottom: 4px;
}

.welcome-brand h1 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.02em;
}

.subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}

/* ── Section blocks ───────────────────────────────────────── */
.col-section h2 {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 11px;
  color: var(--text-muted);
}

.col-section p {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 8px 0;
  line-height: 1.55;
}

.col-section p:last-child { margin-bottom: 0; }

.col-section strong {
  color: var(--text-primary);
  font-weight: 600;
}

/* ── Workflow list ────────────────────────────────────────── */
.workflow-list {
  list-style: none;
  counter-reset: wf;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.workflow-list li {
  counter-increment: wf;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.workflow-list li::before {
  content: counter(wf);
  min-width: 20px;
  height: 20px;
  background: var(--accent-blue-bg);
  color: var(--accent-blue);
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 1px;
}

/* ── Format list ──────────────────────────────────────────── */
.format-list {
  list-style: none;
  padding: 0;
  margin: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.format-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.fmt-badge {
  display: inline-block;
  background: var(--bg-canvas);
  border: 1px solid var(--border-default);
  border-radius: 3px;
  padding: 1px 6px;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--text-primary);
  min-width: 42px;
  text-align: center;
}

/* ── Info box (profiles) ──────────────────────────────────── */
.info-box {
  background: var(--bg-canvas);
  border: 1px solid var(--border-muted);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}

.info-box ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-box li {
  font-size: 13px;
  color: var(--text-secondary);
  padding-left: 14px;
  position: relative;
  line-height: 1.5;
}

.info-box li::before {
  content: '·';
  position: absolute;
  left: 4px;
  color: var(--text-muted);
}

/* ── Path box ─────────────────────────────────────────────── */
.path-box {
  background: var(--bg-canvas);
  border: 1px solid var(--border-muted);
  border-radius: var(--radius-sm);
  padding: 7px 10px;
  margin: 6px 0;
  font-family: var(--font-mono);
}

.path-box code {
  font-size: 12px;
  color: var(--accent-green);
}

/* ── Tip block ────────────────────────────────────────────── */
.tip {
  background: var(--accent-blue-bg);
  border-left: 3px solid var(--accent-blue);
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--accent-blue);
  margin-top: 4px;
}

/* ── Footer ───────────────────────────────────────────────── */
.welcome-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 28px;
  border-top: 1px solid var(--border-default);
  background: var(--bg-panel-header);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  color: var(--text-secondary);
  font-size: 13px;
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
  padding: 8px 28px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: background 0.12s;
}

.start-btn:hover { background: #2560d4; }

/* ── Contact ─────────────────────────────────────────────── */
.contact-emails {
  margin: 4px 0 0 0;
  font-size: 13px;
  color: var(--text-secondary);
}
.contact-link {
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: var(--accent-blue);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
  font-family: var(--font-mono);
}
.contact-link:hover {
  color: var(--accent-blue-hover, #78b8ff);
}

/* ── About / Credits ─────────────────────────────────────── */
.about-maintainers {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 8px 0;
  line-height: 1.55;
}
.paper-link {
  display: block;
  background: none;
  border: 1px solid var(--border-muted);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 500;
  color: var(--accent-blue);
  cursor: pointer;
  text-align: left;
  text-decoration: underline;
  text-underline-offset: 2px;
  line-height: 1.5;
  width: 100%;
  margin-bottom: 6px;
}
.paper-link:hover {
  background: var(--bg-canvas);
  color: var(--accent-blue-hover, #78b8ff);
}
.paper-authors {
  font-size: 11px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.55;
  font-style: italic;
}

/* ── Mobile (≤ 768px) ─────────────────────────────────────── */
@media (max-width: 768px) {
  .welcome-overlay { padding: 0; }

  .welcome-modal {
    width: 100vw;
    max-width: 100vw;
    height: 100vh;
    height: 100dvh;
    border-radius: 0;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }

  .welcome-body { flex-direction: column; overflow-y: auto; }
  .col-divider { display: none; }
  .welcome-col { padding: 20px 16px 16px; gap: 16px; overflow: visible; }

  .welcome-footer {
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    position: sticky;
    bottom: 0;
    background: var(--bg-panel-header);
  }
  .start-btn { width: 100%; min-height: 44px; text-align: center; }
}
</style>
