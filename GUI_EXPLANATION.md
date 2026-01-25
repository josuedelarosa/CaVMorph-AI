# Understanding the Architecture

## ⚠️ Important: Backend API ≠ GUI

The backend API (`http://127.0.0.1:8008`) is **just a web server**, not a GUI application.

```
┌─────────────────────────────────────────┐
│  BACKEND (No GUI)                       │
├─────────────────────────────────────────┤
│  FastAPI Server on http://127.0.0.1:8008│
│  - Accepts HTTP requests                │
│  - Runs inference                       │
│  - Returns JSON responses               │
│  - Text output only                     │
└─────────────────────────────────────────┘
           ↑
           │ HTTP calls from...
           │
┌─────────────────────────────────────────┐
│  FRONTEND (GUI - This is what you see)  │
├─────────────────────────────────────────┤
│  Tauri Desktop App                      │
│  - Vue 3 + TypeScript                   │
│  - Professional UI                      │
│  - File picker                          │
│  - Progress bar                         │
│  - Results table                        │
│  - Export buttons                       │
└─────────────────────────────────────────┘
```

## ✅ How to Actually Use It

### Step 1: Start the Backend (in Terminal 1)
```bash
conda activate cavfish310
python3 -m backend.api.cli --port 8008
```
✅ You'll see: `Uvicorn running on http://127.0.0.1:8008`  
❌ No GUI appears (it's just a server!)

### Step 2: Start the Frontend (in Terminal 2)
```bash
cd desktop/src-tauri
cargo tauri dev
```
✅ A **native desktop window** will open with the full UI!

## 🎯 The GUI You're Looking For

The GUI is the **Tauri desktop app** that opens in Step 2, NOT the HTTP endpoint.

When you visit `http://127.0.0.1:8008` in a browser, you just see the API documentation (OpenAPI/Swagger UI), not the main application.

## 🚀 Quick Start (Development)

### Terminal 1: Backend API Server
```bash
conda activate cavfish310
cd /path/to/cavfish-inference
python3 -m backend.api.cli --port 8008
# Output: Uvicorn running on http://127.0.0.1:8008
# No GUI, just server logs
```

### Terminal 2: Frontend Desktop App
```bash
cd /path/to/cavfish-inference/desktop/src-tauri
cargo tauri dev
# Output: Opens a native window with full GUI!
```

**NOW** you have the full application with:
- ✅ Folder picker
- ✅ Analyze button
- ✅ Progress bar
- ✅ Keypoint preview
- ✅ Results table
- ✅ Export buttons
- ✅ Dark mode toggle

## 📝 For Production (Build)

The `./build.sh` script creates:
1. **Backend binary** (PyInstaller) - ~500MB self-contained executable
2. **Frontend bundle** (Vite) - Static HTML/CSS/JS
3. **Desktop app** (Tauri) - Native wrapper that:
   - Spawns backend binary
   - Loads frontend in native WebView
   - Handles file dialogs, system integration, etc.

Result: Single `.dmg` / `.exe` / `.deb` file that users can download and run.

## 🔧 Troubleshooting

**Q: I started backend but don't see a GUI**  
A: You need to start the **Tauri app** in another terminal (`cargo tauri dev`)

**Q: I visit http://127.0.0.1:8008 and just see API docs**  
A: That's the **API endpoint**, not the GUI. Run `cargo tauri dev` to see the UI.

**Q: PyInstaller failed in build.sh**  
A: It's building now (takes ~2-5 minutes). Be patient!

**Q: build.sh is slow**  
A: First build bundles all dependencies. Subsequent builds are faster.

## ✅ Correct Workflow

```
Terminal 1: Backend (server, no GUI)
│
├─ conda activate cavfish310
├─ python3 -m backend.api.cli --port 8008
└─ [waits for HTTP requests]

Terminal 2: Frontend (GUI app, what you see)
│
├─ cd desktop/src-tauri
├─ cargo tauri dev
└─ [opens native window with full UI]

Terminal 3: Your browser (optional)
│
└─ Visit http://127.0.0.1:8008/docs
   [optional: API documentation]
```

---

The **GUI application is Tauri** (`cargo tauri dev`), not the HTTP API.

Start both terminals and you'll have the full experience!
