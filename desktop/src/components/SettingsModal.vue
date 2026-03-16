<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="close">
    <div class="modal-content settings-modal">

      <!-- Header -->
      <div class="modal-header">
        <h2>Profile Settings</h2>
        <button class="close-btn" @click="close">×</button>
      </div>

      <!-- Two-column body -->
      <div class="modal-body">

        <!-- ─── Left column: profile list + create form ─────────── -->
        <div class="col-left">

          <!-- Profile list -->
          <div class="col-section">
            <div class="col-section-title">Profiles</div>
            <div class="profile-list">
              <div
                v-for="profile in profiles"
                :key="profile.id"
                class="profile-item"
                :class="{ 'profile-active': selectedProfileId === profile.id }"
                @click="selectProfile(profile.id)"
              >
                <div class="profile-radio">
                  <span class="radio-dot" :class="{ active: selectedProfileId === profile.id }"></span>
                </div>
                <div class="profile-info">
                  <div class="profile-name-row">
                    <span class="profile-name">{{ profile.name }}</span>
                    <span v-if="selectedProfileId === profile.id" class="badge-active">Active</span>
                  </div>
                  <div v-if="profile.description" class="profile-desc">{{ profile.description }}</div>
                  <div v-if="profile.folder_path" class="profile-path">{{ profile.folder_path }}</div>
                </div>
                <div class="profile-actions">
                  <button
                    v-if="profile.id !== 'default'"
                    class="btn-icon-danger"
                    @click.stop="deleteCurrentProfile(profile.id)"
                    title="Delete profile"
                  >×</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Create new profile -->
          <div class="col-section create-section">
            <div class="col-section-title">New Profile</div>
            <div class="create-form">
              <input
                v-model="newProfileName"
                placeholder="Profile name"
                class="form-input"
                @keydown.enter="createNewProfile"
              />
              <input
                v-model="newProfileDesc"
                placeholder="Description (optional)"
                class="form-input"
              />
              <button class="btn btn-create" @click="createNewProfile">
                + Create Profile
              </button>
            </div>
          </div>

        </div><!-- /.col-left -->

        <!-- Column divider -->
        <div class="col-divider"></div>

        <!-- ─── Right column: keypoints for active profile ──────── -->
        <div class="col-right">
          <div class="col-section-title">
            Keypoints
            <span class="col-section-sub">for: {{ currentProfile?.name ?? '—' }}</span>
          </div>
          <p class="keypoint-hint">Select the landmarks to detect for this profile.</p>
          <div class="keypoint-scroll">
            <label
              v-for="kp in KEYPOINT_DEFS"
              :key="kp.id"
              class="keypoint-row"
              :class="{ 'kp-checked': isKeypointSelected(kp.id - 1) }"
            >
              <input
                type="checkbox"
                :checked="isKeypointSelected(kp.id - 1)"
                @change="toggleKeypoint(kp.id - 1)"
              />
              <span class="kp-num">{{ kp.id }}</span>
              <span class="kp-label">{{ kp.name }}</span>
            </label>
          </div>
          <div class="kp-summary">
            {{ selectedKeypoints.size }} / {{ KEYPOINT_DEFS.length }} selected
          </div>
        </div><!-- /.col-right -->

      </div><!-- /.modal-body -->

      <!-- Footer -->
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="close">Cancel</button>
        <button class="btn btn-primary" @click="saveSettings">Save Changes</button>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Profile } from '../types'

interface Props {
  isOpen: boolean
  profiles: Profile[]
  activeProfileId: string
  keypointNames: string[]
}

interface Emits {
  (e: 'close'): void
  (e: 'save', data: {
    activeProfileId: string
    selectedKeypoints: number[]
    newProfile?: { name: string; description: string }
  }): void
  (e: 'delete', profileId: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// ── Anatomical keypoint definitions ──────────────────────────────────────────
const KEYPOINT_DEFS = [
  { id:  1, name: 'Anterior snout / upper jaw tip' },
  { id:  2, name: 'Caudal-fin base — standard length endpoint' },
  { id:  3, name: 'Dorsal fin origin' },
  { id:  4, name: 'Ventral body point — body depth reference' },
  { id:  5, name: 'Dorsal head point' },
  { id:  6, name: 'Ventral head point' },
  { id:  7, name: 'Dorsal caudal peduncle' },
  { id:  8, name: 'Ventral caudal peduncle' },
  { id:  9, name: 'Upper caudal fin tip' },
  { id: 10, name: 'Lower caudal fin tip' },
  { id: 11, name: 'Dorsal eye margin' },
  { id: 12, name: 'Ventral eye margin' },
  { id: 13, name: 'Eye center' },
  { id: 14, name: 'Posterior jaw / corner of mouth / jaw articulation' },
  { id: 15, name: 'Pectoral fin origin' },
  { id: 16, name: 'Pectoral fin insertion endpoint' },
  { id: 17, name: 'Posterior opercular margin / posterior head limit' },
  { id: 18, name: 'Distal tip of dorsal fin' },
  { id: 19, name: 'Anal fin origin' },
  { id: 20, name: 'Posterior end of anal fin base' },
]

// ── State ─────────────────────────────────────────────────────────────────────
const selectedProfileId = ref(props.activeProfileId)
const selectedKeypoints = ref<Set<number>>(new Set())
const newProfileName = ref('')
const newProfileDesc = ref('')

const currentProfile = computed(() =>
  props.profiles.find(p => p.id === selectedProfileId.value)
)

// ── Helpers ───────────────────────────────────────────────────────────────────
function isKeypointSelected(idx: number) {
  return selectedKeypoints.value.has(idx)
}

function toggleKeypoint(idx: number) {
  const s = new Set(selectedKeypoints.value)
  if (s.has(idx)) s.delete(idx)
  else s.add(idx)
  selectedKeypoints.value = s
}

function selectProfile(id: string) {
  selectedProfileId.value = id
}

function loadKeypointsForProfile() {
  const profile = props.profiles.find(p => p.id === selectedProfileId.value)
  if (profile) {
    selectedKeypoints.value = new Set(
      profile.selected_keypoints ?? (profile as any).selectedKeypoints ?? []
    )
  }
}

function createNewProfile() {
  if (!newProfileName.value.trim()) return
  emit('save', {
    activeProfileId: selectedProfileId.value,
    selectedKeypoints: Array.from(selectedKeypoints.value),
    newProfile: {
      name: newProfileName.value.trim(),
      description: newProfileDesc.value || 'Custom profile',
    },
  })
  newProfileName.value = ''
  newProfileDesc.value = ''
}

function deleteCurrentProfile(profileId: string) {
  if (confirm('Delete this profile?')) emit('delete', profileId)
}

function saveSettings() {
  emit('save', {
    activeProfileId: selectedProfileId.value,
    selectedKeypoints: Array.from(selectedKeypoints.value),
  })
}

function close() { emit('close') }

// ── Watchers ──────────────────────────────────────────────────────────────────
watch(() => props.activeProfileId, (id) => {
  selectedProfileId.value = id
  loadKeypointsForProfile()
})

watch(() => props.isOpen, (open) => {
  if (open) {
    selectedProfileId.value = props.activeProfileId
    loadKeypointsForProfile()
  }
})

watch(selectedProfileId, () => {
  loadKeypointsForProfile()
})

// Initialize
loadKeypointsForProfile()
</script>

<style scoped>
/* ── Overlay ──────────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
  padding: 24px;
}

/* ── Modal shell ──────────────────────────────────────────── */
.modal-content {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  width: 780px;
  max-width: 96vw;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-overlay);
  overflow: hidden;
}

/* ── Header ───────────────────────────────────────────────── */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-panel-header);
  flex-shrink: 0;
}

.modal-header h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--text-muted);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: color 0.1s, background 0.1s;
}
.close-btn:hover { color: var(--text-primary); background: var(--bg-canvas); }

/* ── Two-column body ──────────────────────────────────────── */
.modal-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.col-left {
  width: 280px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--border-muted);
}

.col-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow: hidden;
}

.col-divider { display: none; } /* handled by border */

.col-section {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-muted);
}

.col-section:last-child { border-bottom: none; }

.col-section-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-muted);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.col-section-sub {
  font-size: 11px;
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
  color: var(--text-secondary);
}

/* ── Profile list ─────────────────────────────────────────── */
.col-left .col-section:first-child {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.profile-list {
  overflow-y: auto;
  flex: 1;
}

.profile-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 4px;
  border-bottom: 1px solid var(--border-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background 0.1s;
}
.profile-item:last-child { border-bottom: none; }
.profile-item:hover { background: var(--bg-canvas); }
.profile-item.profile-active { background: var(--accent-blue-bg); }

.profile-radio { padding-top: 2px; }

.radio-dot {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--border-default);
  background: var(--bg-surface);
  flex-shrink: 0;
  transition: border-color 0.1s, background 0.1s;
}
.radio-dot.active {
  border-color: var(--accent-blue);
  background: var(--accent-blue);
  box-shadow: 0 0 0 2px var(--accent-blue-bg);
}

.profile-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.profile-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.profile-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.badge-active {
  font-size: 10px;
  font-weight: 600;
  background: var(--accent-blue);
  color: #fff;
  padding: 1px 6px;
  border-radius: 10px;
  letter-spacing: 0.03em;
}

.profile-desc {
  font-size: 12px;
  color: var(--text-secondary);
}

.profile-path {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-actions {
  flex-shrink: 0;
}

.btn-icon-danger {
  width: 22px;
  height: 22px;
  background: none;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 15px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.1s, background 0.1s, border-color 0.1s;
  line-height: 1;
}
.btn-icon-danger:hover {
  color: var(--accent-red);
  background: #fef2f2;
  border-color: #fca5a5;
}

/* ── Create form ──────────────────────────────────────────── */
.create-section {
  flex-shrink: 0;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-family: var(--font-sans);
  background: var(--bg-canvas);
  color: var(--text-primary);
  transition: border-color 0.1s;
}
.form-input:focus {
  outline: none;
  border-color: var(--accent-blue);
  box-shadow: 0 0 0 2px var(--accent-blue-bg);
}

.btn-create {
  align-self: flex-start;
  padding: 5px 12px;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-sans);
  background: var(--accent-blue);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.1s;
}
.btn-create:hover { background: #2560d4; }

/* ── Keypoint scroll area ─────────────────────────────────── */
.keypoint-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0 0 10px 0;
}

.keypoint-scroll {
  flex: 1;
  overflow-y: auto;
  border: 1px solid var(--border-muted);
  border-radius: var(--radius-md);
  background: var(--bg-canvas);
  padding: 4px 0;
}

.keypoint-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 12px;
  cursor: pointer;
  transition: background 0.08s;
  border-radius: 0;
}
.keypoint-row:hover { background: var(--bg-surface); }
.keypoint-row.kp-checked { background: var(--accent-blue-bg); }
.keypoint-row.kp-checked:hover { background: #dbeafe; }

.keypoint-row input[type="checkbox"] {
  flex-shrink: 0;
  cursor: pointer;
  accent-color: var(--accent-blue);
  width: 14px;
  height: 14px;
}

.kp-num {
  width: 22px;
  text-align: right;
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-muted);
  flex-shrink: 0;
}

.kp-label {
  font-size: 12px;
  color: var(--text-secondary);
  flex: 1;
  line-height: 1.4;
}

.keypoint-row.kp-checked .kp-label {
  color: var(--text-primary);
  font-weight: 500;
}

.kp-summary {
  font-size: 11px;
  color: var(--text-muted);
  padding-top: 6px;
  text-align: right;
}

/* ── Footer ───────────────────────────────────────────────── */
.modal-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid var(--border-default);
  background: var(--bg-panel-header);
  flex-shrink: 0;
}

/* ── Buttons ──────────────────────────────────────────────── */
.btn {
  padding: 6px 14px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: background 0.1s;
}

.btn-primary {
  background: var(--accent-blue);
  color: #fff;
}
.btn-primary:hover { background: #2560d4; }

.btn-secondary {
  background: var(--bg-surface-raised);
  color: var(--text-primary);
  border-color: var(--border-default);
}
.btn-secondary:hover { background: var(--bg-canvas); }

/* ── Scrollbars ───────────────────────────────────────────── */
.profile-list::-webkit-scrollbar,
.keypoint-scroll::-webkit-scrollbar { width: 6px; }
.profile-list::-webkit-scrollbar-track,
.keypoint-scroll::-webkit-scrollbar-track { background: transparent; }
.profile-list::-webkit-scrollbar-thumb,
.keypoint-scroll::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: 3px; }
</style>
