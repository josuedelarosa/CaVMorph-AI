# Choice Screen Implementation

## Summary
Implemented a user-choice paradigm for the conda environment setup. Instead of automatically detecting and installing, the app now asks the user upfront whether they have the environment already installed.

## Changes Made

### 1. Rust Backend (desktop/src-tauri/src/main.rs)
- **Added `check_conda_env_exists()` command**: Checks if `cavfish310` conda environment exists by looking for the Python executable
- **Registered the new command** in the invoke handler

### 2. Vue Frontend (desktop/src/views/SetupView.vue)
- **Added choice screen UI**: Shows before any setup begins with two options:
  - "Use Existing Environment" - for users who manually installed cavfish310
  - "Create New Environment" - runs the full auto-install process
  
- **Added environment detection**:
  - `checkEnvironment()`: Checks for conda installation and cavfish310 existence
  - Shows green checkmarks when conda/env are found
  - Disables "Use Existing" button if cavfish310 not found

- **Split setup flow**:
  - `useExistingEnv()`: Skips setup and directly calls `finish_setup_and_start`
  - `createNewEnv()`: Runs full `startSetup()` with all installation steps

### 3. User Experience Flow

**On First Launch:**
1. App checks for conda installation → shows path if found
2. App checks for cavfish310 environment → shows status
3. User sees two options:
   - If cavfish310 exists: both buttons enabled
   - If cavfish310 missing: only "Create New Environment" enabled
4. User makes choice:
   - **Use Existing**: App immediately starts backend with their cavfish310 env
   - **Create New**: App runs full setup script with progress tracking

## Benefits
- **No more forced auto-installation**: Users with working setups can bypass it
- **Clear user intent**: Explicit choice instead of fragile detection logic
- **Better error handling**: Users know what they're choosing
- **Faster for existing setups**: Skip 15-30 minute installation entirely

## Testing
To rebuild and test:
```bash
cd desktop
npm install
npm run build
npm run tauri build
```

The app should now show the choice screen on first launch, with the "Use Existing Environment" button enabled if you have cavfish310 installed.

## Future Improvements
- Add "Verify Environment" button to check if existing env has all required packages
- Show environment details (Python version, package versions) before using existing env
- Add option to repair/upgrade existing environment
