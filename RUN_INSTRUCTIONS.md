# 🚀 How to Run Fish Morphometrics

## ⚠️ CRITICAL: Two Separate Applications

This project has **TWO PARTS** that must run together:

### 1. **Backend API** (Server - No GUI)
- Location: `dist/fish_backend` or `python3 -m backend.api.cli`
- Purpose: Runs inference
- Port: 8008 (default)
- **This is JUST a server, not a visual application**

### 2. **Frontend App** (Desktop GUI - What You See)
- Location: Tauri app
- Purpose: User interface
- Command: `cargo tauri dev`
- **This is the actual visual application**

---

## ✅ How to Run (Development)

### Option 1: Using Source Code

**Terminal 1 - Start Backend:**
```bash
conda activate cavfish310
cd /path/to/cavfish-inference
python3 -m backend.api.cli --port 8008
```
✅ You should see: `INFO:     Uvicorn running on http://127.0.0.1:8008`

**Terminal 2 - Start Frontend:**
```bash
cd /path/to/cavfish-inference/desktop/src-tauri
cargo tauri dev
```
✅ A **native desktop window** will open with the full GUI

### Option 2: Using Backend Binary (PyInstaller)

**Terminal 1 - Start Backend Binary:**
```bash
conda activate cavfish310
/path/to/cavfish-inference/dist/fish_backend --port 8008
```
✅ Same output as above

**Terminal 2 - Start Frontend:**
```bash
cd /path/to/cavfish-inference/desktop/src-tauri
cargo tauri dev
```
✅ Same GUI window opens

---

## 🎯 What You Should See

### Terminal 1 (Backend) Output:
```
INFO:     Uvicorn running on http://127.0.0.1:8008 (Press CTRL+C to quit)
INFO:     Application startup complete
```
(This is normal - just the server running)

### Desktop Window (Frontend):
- Title bar: "Fish Morphometrics"
- Menu at top with dark mode toggle
- "Select Folder" button
- Analysis progress bar
- Results table
- Export buttons

---

## ❌ Common Mistakes

### ❌ "I started backend but don't see a GUI"
**Reason**: Backend is just a server. You need Terminal 2 with Tauri.  
**Solution**: Run `cargo tauri dev` in another terminal.

### ❌ "I visit http://127.0.0.1:8008 and see weird JSON"
**Reason**: That's the API endpoint, not the app.  
**Solution**: Run `cargo tauri dev` to see the actual GUI.

### ❌ "Backend won't start with ./build.sh"
**Reason**: PyInstaller needs to be installed.  
**Solution**: 
```bash
conda activate cavfish310
pip install pyinstaller
```
Then run `./build.sh` again.

### ❌ "build.sh takes forever"
**Reason**: First build compiles PyInstaller + packages all libraries (~5 minutes).  
**Solution**: Let it finish. Subsequent builds are much faster.

---

## 📊 Architecture Reminder

```
┌─────────────────────────────────────────┐
│         DESKTOP WINDOW (GUI)            │ ← This is what you see
│  ┌─────────────────────────────────┐   │
│  │  Folder Picker                  │   │
│  │  Analyze Button                 │   │
│  │  Progress Bar                   │   │
│  │  Results Table                  │   │
│  │  Export Buttons                 │   │
│  └─────────────────────────────────┘   │
│           ↓ HTTP calls ↓                │
└─────────────────────────────────────────┘
           ↑
           │
        HTTP://127.0.0.1:8008
           │
        ↓
┌─────────────────────────────────────────┐
│         BACKEND API (No GUI)            │
│  ┌─────────────────────────────────┐   │
│  │  FastAPI Server                 │   │
│  │  - /health endpoint             │   │
│  │  - /infer/image endpoint        │   │
│  │  - /export endpoints            │   │
│  │  - Returns JSON responses       │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## ✅ Correct Full Workflow

```
Step 1: Open Terminal 1
├─ conda activate cavfish310
├─ cd /path/to/cavfish-inference
└─ python3 -m backend.api.cli --port 8008
   [Wait for: "Uvicorn running on http://127.0.0.1:8008"]

Step 2: Open Terminal 2 (while Terminal 1 runs)
├─ cd /path/to/cavfish-inference/desktop/src-tauri
└─ cargo tauri dev
   [Desktop window opens automatically]

Step 3: Use the App
├─ Click "Select Folder"
├─ Pick folder with fish images
├─ Click "Analyze Images"
├─ View results
└─ Export results (CSV/JSON/PNG)

Step 4: Cleanup
└─ Press CTRL+C in both terminals
```

---

## 🔍 Testing Individual Components

### Test Backend Only:
```bash
conda activate cavfish310
python3 -m backend.api.cli --port 8008
curl http://127.0.0.1:8008/health
# Should return: {"ok": true, "device": "cpu", "model_dir": "..."}
```

### Test Frontend Only:
```bash
cd desktop/src-tauri
cargo tauri dev
# Desktop window opens
# Will show connection error (no backend)
```

---

## 💾 Production Mode (Packaged App)

When you run `./build.sh`, it creates:
- Tauri app that includes backend binary
- Single `.dmg` / `.exe` / `.deb` file
- Users just double-click to run (no terminals needed!)

---

## 📝 Summary

**Remember:**
- 🖥️ **Frontend GUI** = `cargo tauri dev`
- 🔧 **Backend Server** = `python3 -m backend.api.cli`
- 📦 **Both together** = Full working application
- ❌ **Frontend only** = "Connection error"
- ❌ **Backend only** = No GUI to interact with

**Always run both terminals!**

---

If you have issues, check:
1. Both terminals running?
2. `conda activate cavfish310` before starting?
3. Using `python3` (not `python`)?
4. Backend on port 8008?
5. Frontend can connect to backend?

