# AMFI Fix Implementation Summary

## Problem
macOS AMFI (Apple Mobile File Integrity) was blocking the app as "damaged/modified" because Python was writing `__pycache__` directories and `.pyc` bytecode files inside the `.app` bundle, which invalidates the code signature.

## Solution Implemented

### 1. ✅ Disabled Python Bytecode Generation
**File:** `desktop/src-tauri/src/main.rs`

Added environment variable before Python startup:
```rust
cmd.env("PYTHONDONTWRITEBYTECODE", "1");
```

### 2. ✅ Redirected All Python Cache Files Outside .app Bundle
**File:** `desktop/src-tauri/src/main.rs`

Created cache directories in `~/Library/Caches/FishMorphometrics/`:
- `pycache/` - Python bytecode cache
- `torch/` - PyTorch model cache  
- `matplotlib/` - Matplotlib config cache

Added environment variables:
```rust
cmd.env("PYTHONPYCACHEPREFIX", pycache_dir);
cmd.env("XDG_CACHE_HOME", cache_base);
cmd.env("TORCH_HOME", torch_cache);
cmd.env("MPLCONFIGDIR", mpl_cache);
```

### 3. ✅ Cache Directory Creation at Startup
**File:** `desktop/src-tauri/src/main.rs`

Automatically creates cache directories before spawning Python:
```rust
let cache_base = home_dir.join("Library/Caches/FishMorphometrics");
let _ = fs::create_dir_all(&pycache_dir);
let _ = fs::create_dir_all(&torch_cache);
let _ = fs::create_dir_all(&mpl_cache);
```

### 4. ✅ Build-Time Cleanup
**Files:** `desktop/clean-python-cache.sh`, `desktop/build-dmg.sh`

Created cleanup script that removes from built app:
- All `__pycache__/` directories
- All `.pyc` files
- All `.pyo` files

Integrated into build process:
```bash
./build-dmg.sh  # Now includes automatic cache cleanup
```

## Directory Structure

### Before (❌ Breaks AMFI):
```
Fish Morphometrics.app/
└── Contents/
    └── Resources/
        └── _up_/_up_/backend/
            ├── api/
            │   ├── __pycache__/     ← Written at runtime!
            │   └── app.py
            └── cavfish/
                ├── __pycache__/     ← Written at runtime!
                └── infer.py
```

### After (✅ AMFI-Safe):
```
Fish Morphometrics.app/
└── Contents/
    └── Resources/
        └── _up_/_up_/backend/
            ├── api/
            │   └── app.py           ← No __pycache__!
            └── cavfish/
                └── infer.py         ← No __pycache__!

~/Library/Caches/FishMorphometrics/  ← All caches here
├── pycache/
├── torch/
└── matplotlib/
```

## How It Works

1. **At Build Time:**
   - `build-dmg.sh` runs Tauri build
   - `clean-python-cache.sh` removes all `.pyc` and `__pycache__` from built app
   - DMG is created with clean, immutable app bundle

2. **At Runtime:**
   - Rust code creates cache directories in `~/Library/Caches/`
   - Environment variables redirect all Python caching outside `.app`
   - `PYTHONDONTWRITEBYTECODE=1` prevents any `.pyc` creation
   - App bundle remains unchanged → AMFI stays happy

## Testing

To test the fix:

1. **Build the app:**
   ```bash
   cd desktop
   ./build-dmg.sh
   ```

2. **Verify cleanup:**
   ```bash
   # Should find NO __pycache__ or .pyc files
   find "src-tauri/target/release/bundle/macos/Fish Morphometrics.app" \
        -name "__pycache__" -o -name "*.pyc"
   ```

3. **Install and run:**
   - Install from DMG
   - Run the app
   - Check that caches are in `~/Library/Caches/FishMorphometrics/`
   - macOS should not mark app as "damaged"

## Expected Behavior

- ✅ App installs normally
- ✅ Gatekeeper shows standard "Open anyway" option (if unsigned)
- ✅ No "damaged or incomplete" errors
- ✅ Python runs normally with caches in user directory
- ✅ App bundle remains immutable after installation

## Next Build Steps

When ready to rebuild:
```bash
cd /Users/josuedelarosa/Documents/BIVL2ab/projects/cavfish_repo/cavfish-inference/desktop
./build-dmg.sh
```

This will:
1. Build the Tauri app
2. Clean all Python bytecode
3. Create DMG with Applications shortcut
4. App will now be AMFI-compliant
