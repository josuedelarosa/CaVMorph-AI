import { appDataDir } from '@tauri-apps/api/path'
import { readTextFile, writeTextFile, createDir } from '@tauri-apps/api/fs'
import type { AppConfig, Profile } from '../types'

const CONFIG_FILE = 'fish_morphometrics_config.json'

const DEFAULT_CONFIG: AppConfig = {
  activeProfileId: 'default',
  profiles: [
    {
      id: 'default',
      name: 'Standard Fish',
      description: 'All 20 keypoints',
      selectedKeypoints: Array.from({ length: 20 }, (_, i) => i),
      selected_keypoints: Array.from({ length: 20 }, (_, i) => i),
      createdAt: Date.now(),
      enabled: true,
      folder_path: undefined,
    },
  ],
  darkMode: false,
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
  try {
    await ensureConfigDir()
    const path = await getConfigPath()
    const content = await readTextFile(path)
    return JSON.parse(content)
  } catch {
    return DEFAULT_CONFIG
  }
}

export async function saveConfig(config: AppConfig): Promise<void> {
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
