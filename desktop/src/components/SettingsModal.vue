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
              ➕ Create Profile
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
                  <small>📁 {{ profile.folder_path }}</small>
                </div>
              </div>
              <button
                v-if="profile.id !== 'default'"
                @click="deleteCurrentProfile(profile.id)"
                class="btn btn-sm btn-danger"
              >
                🗑️ Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button @click="saveSettings" class="btn btn-primary">✓ Save</button>
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
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.settings-modal {
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
}

.modal-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}

.settings-section {
  margin-bottom: 25px;
}

.settings-section h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  color: #666;
}

.form-select,
.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  margin-bottom: 10px;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: #0066ff;
  box-shadow: 0 0 0 3px rgba(0, 102, 255, 0.1);
}

.keypoint-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}

.keypoint-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.keypoint-checkbox:hover {
  background: #f5f5f5;
}

.keypoint-checkbox input {
  cursor: pointer;
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 15px;
}

.profile-list {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.profile-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.profile-item:last-child {
  border-bottom: none;
}

.profile-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.profile-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 12px;
  color: #666;
}

.toggle-label input {
  cursor: pointer;
}

.profile-folder {
  color: #666;
  font-family: monospace;
  font-size: 11px;
}

.profile-info small {
  color: #999;
  font-size: 12px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #000;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #0066ff;
  color: white;
}

.btn-primary:hover {
  background: #0052cc;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.btn-danger {
  background: #ff4444;
  color: white;
}

.btn-danger:hover {
  background: #dd0000;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
