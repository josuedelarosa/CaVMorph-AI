# Profile System Documentation

## Overview
The profile system allows users to create and switch between different fish phenotyping configurations. Each profile can have a custom selection of keypoints, which automatically filters phenotypes and visualizations.

## Features

### Profile Management
- **Create profiles** for different fish types (e.g., "Standard Fish", "Compressed Fish", "Depressed Cavfish")
- **Select keypoints** for each profile - only selected keypoints are displayed and used for phenotype calculations
- **Persistent storage** - profiles are saved to disk and restored when the app reopens
- **Default profile** - "Standard Fish" includes all 20 keypoints

### Keypoint Filtering
- When you select a subset of keypoints for a profile, only those keypoints are:
  - Displayed on the canvas preview
  - Used to calculate phenotypes
  - Included in exports (CSV, JSON)

### Phenotype Filtering
- Phenotypes are automatically filtered based on the selected keypoints
- A phenotype is only shown if **both** of its keypoints are selected in the active profile
- Example: If keypoints 3 and 4 are not selected, any phenotype pair (3,4) will be hidden

## UI Usage

### Opening Settings
1. Click the **⚙️ settings button** in the top-right corner (next to dark mode toggle)
2. The Settings Modal will open

### Creating a Profile
1. Open Settings
2. Scroll to "Manage Profiles" section
3. Enter a profile name and description
4. Select the keypoints you want to include
5. Click "➕ Create Profile"
6. Click "✓ Save"

### Switching Profiles
1. Open Settings
2. Use the "Active Profile" dropdown to select a different profile
3. Click "✓ Save"

### Editing a Profile
1. Open Settings
2. Select the profile from "Active Profile" dropdown
3. Toggle keypoints on/off
4. Click "✓ Save"

### Deleting a Profile
1. Open Settings
2. Click "🗑️ Delete" next to the profile name
3. Note: Default profile cannot be deleted

## Data Structure

Profiles are stored in `~/.config/fish_morphometrics/fish_morphometrics_config.json`:

```json
{
  "activeProfileId": "default",
  "profiles": [
    {
      "id": "default",
      "name": "Standard Fish",
      "description": "All 20 keypoints",
      "selectedKeypoints": [0, 1, 2, ..., 19],
      "createdAt": 1704067200000
    },
    {
      "id": "profile_1704067200000",
      "name": "Compressed Fish",
      "description": "No mouth/gills",
      "selectedKeypoints": [0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
      "createdAt": 1704067250000
    }
  ],
  "darkMode": false
}
```

## Technical Implementation

### Files Modified
- `src/types/index.ts` - Added Profile and AppConfig interfaces
- `src/App.vue` - Integrated profile system, keypoint filtering
- `src/components/SettingsModal.vue` - New settings UI component
- `src/utils/storage.ts` - New file for persistent storage with Tauri

### Key Functions
- `loadConfig()` - Load profiles from disk
- `saveConfig()` - Save profiles to disk
- `createProfile()` - Create new profile
- `updateProfile()` - Edit existing profile
- `deleteProfile()` - Remove profile
- `setActiveProfile()` - Switch active profile
- `setDarkMode()` - Persist dark mode preference

### Keypoint Filtering Logic
In `App.vue`:
1. Canvas rendering filters keypoints via `selectedKeypoints.value.has(i)`
2. Phenotype columns filter via keypoint pair checking
3. Export functions can be extended to filter phenotypes before export

## Future Enhancements
- Import/export profiles as JSON files
- Preset profiles bundled with app for common fish species
- Batch validation: ensure keypoint pairs exist before calculating phenotypes
- Profile sharing between users
