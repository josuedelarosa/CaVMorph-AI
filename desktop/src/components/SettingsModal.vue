<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="close">
    <div class="modal-content settings-modal">
      <div class="modal-header">
        <h2>Profile Settings</h2>
        <button class="close-btn" @click="close">×</button>
      </div>

      <div class="modal-body">
        <!-- Profile Selection -->
        <div class="settings-section">
          <h3>Active Profile</h3>
          <select v-model="selectedProfileId" class="form-select">
            <option v-for="profile in profiles" :key="profile.id" :value="profile.id">
              {{ profile.name }}
            </option>
          </select>
        </div>

        <!-- Keypoint Selection -->
        <div class="settings-section">
          <h3>Selected Keypoints</h3>
          <div class="keypoint-grid">
            <label v-for="(name, idx) in keypointNames" :key="idx" class="keypoint-checkbox">
              <input
                type="checkbox"
                :checked="isKeypointSelected(idx)"
                @change="toggleKeypoint(idx)"
              />
              <span>{{ idx + 1 }}: {{ name }}</span>
            </label>
          </div>
        </div>

        <!-- Profile Management -->
        <div class="settings-section">
          <h3>Manage Profiles</h3>
          <div class="profile-form">
            <input v-model="newProfileName" placeholder="Profile name" class="form-input" />
            <input v-model="newProfileDesc" placeholder="Description" class="form-input" />
            <button @click="createNewProfile" class="btn btn-sm btn-primary">
              Create Profile
            </button>
          </div>

          <div v-if="profiles.length > 1" class="profile-list">
            <div v-for="profile in profiles" :key="profile.id" class="profile-item">
              <div class="profile-info">
                <div class="profile-header-row">
                  <strong>{{ profile.name }}</strong>
                  <label class="toggle-label">
                    <input type="checkbox" :checked="profile.enabled" @change="toggleProfileEnabled(profile.id)" />
                    <span>{{ profile.enabled ? 'Enabled' : 'Disabled' }}</span>
                  </label>
                </div>
                <small>{{ profile.description }}</small>
                <div class="profile-folder" v-if="profile.folder_path">
                  <small>{{ profile.folder_path }}</small>
                </div>
              </div>
              <button
                v-if="profile.id !== 'default'"
                @click="deleteCurrentProfile(profile.id)"
                class="btn btn-sm btn-danger"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button @click="saveSettings" class="btn btn-primary">Save</button>
        <button @click="close" class="btn btn-secondary">Cancel</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
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

const selectedProfileId = ref(props.activeProfileId)
const selectedKeypoints = ref<Set<number>>(new Set())
const newProfileName = ref('')
const newProfileDesc = ref('')

const currentProfile = computed(() => props.profiles.find((p) => p.id === selectedProfileId.value))

const isKeypointSelected = (idx: number) => selectedKeypoints.value.has(idx)

const toggleKeypoint = (idx: number) => {
  if (selectedKeypoints.value.has(idx)) {
    selectedKeypoints.value.delete(idx)
  } else {
    selectedKeypoints.value.add(idx)
  }
}

const createNewProfile = () => {
  if (!newProfileName.value.trim()) {
    alert('Profile name is required')
    return
  }

  emit('save', {
    activeProfileId: selectedProfileId.value,
    selectedKeypoints: Array.from(selectedKeypoints.value),
    newProfile: {
      name: newProfileName.value,
      description: newProfileDesc.value || 'Custom profile',
    },
  })

  newProfileName.value = ''
  newProfileDesc.value = ''
}

const deleteCurrentProfile = (profileId: string) => {
  if (confirm('Delete this profile?')) {
    emit('delete', profileId)
  }
}

const toggleProfileEnabled = (profileId: string) => {
  const profileIdx = props.profiles.findIndex(p => p.id === profileId)
  if (profileIdx !== -1) {
    props.profiles[profileIdx].enabled = !props.profiles[profileIdx].enabled
  }
}

const saveSettings = () => {
  emit('save', {
    activeProfileId: selectedProfileId.value,
    selectedKeypoints: Array.from(selectedKeypoints.value),
  })
}

const close = () => emit('close')

// Initialize selected keypoints when profile changes
const updateSelectedKeypoints = () => {
  if (currentProfile.value) {
    selectedKeypoints.value = new Set(currentProfile.value.selected_keypoints || currentProfile.value.selectedKeypoints || [])
  }
}

// Watch for profile changes
import { watch } from 'vue'
watch(() => props.activeProfileId, () => {
  selectedProfileId.value = props.activeProfileId
  updateSelectedKeypoints()
})

// Watch when modal opens to reload keypoints
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    selectedProfileId.value = props.activeProfileId
    updateSelectedKeypoints()
  }
})

// Watch for profile selection changes in the dropdown
watch(selectedProfileId, () => {
  updateSelectedKeypoints()
})

// Initialize on mount
updateSelectedKeypoints()
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal-content {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 640px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: var(--shadow-overlay);
}

.settings-modal {
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--sp-16);
  border-bottom: 1px solid var(--border-default);
}

.modal-header h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-body {
  padding: var(--sp-16);
  flex: 1;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  gap: var(--sp-8);
  justify-content: flex-end;
  padding: var(--sp-12) var(--sp-16);
  border-top: 1px solid var(--border-default);
}

.settings-section {
  margin-bottom: 20px;
}

.settings-section h3 {
  margin: 0 0 var(--sp-8) 0;
  font-size: var(--fs-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.form-select,
.form-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--fs-sm);
  font-family: var(--font-sans);
  margin-bottom: var(--sp-8);
  background: var(--bg-canvas);
  color: var(--text-primary);
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: var(--accent-blue);
  box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.15);
}

.keypoint-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--sp-4);
}

.keypoint-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 5px var(--sp-8);
  border-radius: var(--radius-sm);
  transition: background 0.12s;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}

.keypoint-checkbox:hover {
  background: var(--bg-overlay);
}

.keypoint-checkbox input {
  cursor: pointer;
  accent-color: var(--accent-blue);
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-8);
  margin-bottom: var(--sp-12);
}

.profile-list {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  max-height: 200px;
  overflow-y: auto;
}

.profile-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--sp-8) var(--sp-12);
  border-bottom: 1px solid var(--border-muted);
}

.profile-item:last-child {
  border-bottom: none;
}

.profile-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.profile-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-12);
}

.profile-header-row strong {
  color: var(--text-primary);
  font-size: var(--fs-sm);
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: var(--fs-xs);
  color: var(--text-secondary);
}

.toggle-label input {
  cursor: pointer;
  accent-color: var(--accent-blue);
}

.profile-folder {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
}

.profile-info small {
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--text-muted);
  padding: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: color 0.12s, background 0.12s;
}

.close-btn:hover {
  color: var(--text-primary);
  background: var(--bg-overlay);
}

.btn {
  padding: 5px 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-family: var(--font-sans);
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
  line-height: 20px;
}

.btn-primary {
  background: var(--accent-blue);
  color: var(--text-on-emphasis);
}

.btn-primary:hover {
  background: #4c9aed;
}

.btn-secondary {
  background: var(--bg-overlay);
  color: var(--text-primary);
  border-color: var(--border-default);
}

.btn-secondary:hover {
  background: var(--bg-surface-raised);
}

.btn-danger {
  background: rgba(248, 81, 73, 0.15);
  color: var(--accent-red);
  border-color: rgba(248, 81, 73, 0.3);
}

.btn-danger:hover {
  background: rgba(248, 81, 73, 0.25);
}

.btn-sm {
  padding: 2px 8px;
  font-size: var(--fs-xs);
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
</style>
