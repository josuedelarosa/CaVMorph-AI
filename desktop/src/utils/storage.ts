import {
  isTauri,
  appDataDir,
  readTextFile,
  writeTextFile,
  createDir,
} from './platform'
import type { AppConfig, Profile } from '../types'

const CONFIG_FILE = 'fish_morphometrics_config.json'
const LOCAL_STORAGE_KEY = 'phenoai_config'

// Built-in preset profiles — always available, cannot be deleted
export const PRESET_PROFILES: import('../types').Profile[] = [
  {
    id: 'preset-all',
    name: 'Compressed',
    description: 'All 20 landmarks for compressed body morphology',
    selectedKeypoints: Array.from({ length: 20 }, (_, i) => i),
    selected_keypoints: Array.from({ length: 20 }, (_, i) => i),
    createdAt: 0,
    enabled: true,
    folder_path: undefined,
    isBuiltIn: true,
  },
  {
    id: 'preset-depressed',
    name: 'Depressed',
    description: 'Depressed morphology (no corner of mouth, KP 14)',
    selectedKeypoints: [0,1,2,3,4,5,6,7,8,9,10,11,12,14,15,16,17,18,19],
    selected_keypoints: [0,1,2,3,4,5,6,7,8,9,10,11,12,14,15,16,17,18,19],
    createdAt: 0,
    enabled: true,
    folder_path: undefined,
    isBuiltIn: true,
  },
  {
    id: 'preset-no-caudal',
    name: 'No Caudal Fin',
    description: 'Without caudal fin (no KP 9, 10, 14, 18)',
    selectedKeypoints: [0,1,2,3,4,5,6,7,10,11,12,14,15,16,18,19],
    selected_keypoints: [0,1,2,3,4,5,6,7,10,11,12,14,15,16,18,19],
    createdAt: 0,
    enabled: true,
    folder_path: undefined,
    isBuiltIn: true,
  },
]

const DEFAULT_CONFIG: import('../types').AppConfig = {
  activeProfileId: 'preset-all',
  profiles: PRESET_PROFILES,
  darkMode: false,
  contributionOptIn: false,
  anonymousId: '',
}

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  // Fallback for environments without crypto.randomUUID
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

async function getConfigPath(): Promise<string> {
  const dataDir = await appDataDir()
  return `${dataDir}${CONFIG_FILE}`
}

async function ensureConfigDir(): Promise<void> {
  try {
    const dataDir = await appDataDir()
    await createDir(dataDir, { recursive: true })
  } catch {
    // Directory might already exist
  }
}

export async function loadConfig(): Promise<AppConfig> {
  if (!isTauri) {
    // Web mode — use localStorage
    try {
      const raw = localStorage.getItem(LOCAL_STORAGE_KEY)
      if (raw) {
        const saved: AppConfig = JSON.parse(raw)
        const userProfiles = saved.profiles.filter(p => !p.isBuiltIn && p.id !== 'default')
        saved.profiles = [...PRESET_PROFILES, ...userProfiles]
        if (!saved.profiles.some(p => p.id === saved.activeProfileId)) {
          saved.activeProfileId = PRESET_PROFILES[0].id
        }
        return saved
      }
    } catch { /* fall through */ }
    return DEFAULT_CONFIG
  }

  // Tauri mode — filesystem
  try {
    await ensureConfigDir()
    const path = await getConfigPath()
    const content = await readTextFile(path)
    const saved: AppConfig = JSON.parse(content)
    // Always ensure preset profiles are present (and up-to-date)
    const userProfiles = saved.profiles.filter(p => !p.isBuiltIn && p.id !== 'default')
    saved.profiles = [...PRESET_PROFILES, ...userProfiles]
    // If saved activeProfileId no longer exists, fall back to first preset
    if (!saved.profiles.some(p => p.id === saved.activeProfileId)) {
      saved.activeProfileId = PRESET_PROFILES[0].id
    }
    return saved
  } catch {
    return DEFAULT_CONFIG
  }
}

export async function saveConfig(config: AppConfig): Promise<void> {
  if (!isTauri) {
    // Web mode — localStorage
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(config))
    return
  }

  // Tauri mode — filesystem
  await ensureConfigDir()
  const path = await getConfigPath()
  await writeTextFile(path, JSON.stringify(config, null, 2))
}

export async function createProfile(name: string, description: string, selectedKeypoints: number[]): Promise<Profile> {
  const profile: Profile = {
    id: `profile_${Date.now()}`,
    name,
    description,
    selectedKeypoints,
    selected_keypoints: selectedKeypoints,
    createdAt: Date.now(),
    enabled: true,
    folder_path: undefined,
  }

  const config = await loadConfig()
  config.profiles.push(profile)
  await saveConfig(config)

  return profile
}

export async function updateProfile(id: string, updates: Partial<Profile>): Promise<void> {
  const config = await loadConfig()
  const idx = config.profiles.findIndex((p) => p.id === id)
  if (idx !== -1) {
    config.profiles[idx] = { ...config.profiles[idx], ...updates }
    await saveConfig(config)
  }
}

export async function deleteProfile(id: string): Promise<void> {
  const config = await loadConfig()
  config.profiles = config.profiles.filter((p) => p.id !== id)

  if (config.activeProfileId === id) {
    config.activeProfileId = config.profiles[0]?.id || 'default'
  }

  await saveConfig(config)
}

export async function setActiveProfile(id: string): Promise<void> {
  const config = await loadConfig()
  if (config.profiles.some((p) => p.id === id)) {
    config.activeProfileId = id
    await saveConfig(config)
  }
}

export async function getActiveProfile(): Promise<Profile | null> {
  const config = await loadConfig()
  return config.profiles.find((p) => p.id === config.activeProfileId) || null
}

export async function setDarkMode(isDark: boolean): Promise<void> {
  const config = await loadConfig()
  config.darkMode = isDark
  await saveConfig(config)
}

export async function setContributionOptIn(value: boolean): Promise<void> {
  const config = await loadConfig()
  await saveConfig({ ...config, contributionOptIn: value })
}

export async function getOrCreateAnonymousId(): Promise<string> {
  const config = await loadConfig()
  if (config.anonymousId) return config.anonymousId
  const id = generateUUID()
  await saveConfig({ ...config, anonymousId: id })
  return id
}
