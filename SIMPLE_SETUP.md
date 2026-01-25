# 🚀 SIMPLE SETUP - Just Follow These Steps

## What You Need (Two Terminals)

### Terminal 1: Keep Backend Running (Don't Close It!)

```bash
conda activate cavfish310
python3 -m backend.api.cli --port 8008
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8008 (Press CTRL+C to quit)
```

⚠️ **IMPORTANT**: Don't press CTRL+C! Keep this running.

---

### Terminal 2: Run Desktop App (In a NEW Terminal)

```bash
cd ~/Documents/BIVL2ab/projects/cavfish-inference/desktop/src-tauri
source ~/.cargo/env
cargo tauri dev
```

**Expected output:**
```
VITE v5.4.21 ready in X ms
Watching for changes...
Finished `dev` profile [unoptimized + debuginfo] target(s) in X.XXs
```

A **native desktop window** should open automatically.

---

## What Happens Next

1. **Desktop window opens** with "Fish Morphometrics" title
2. **Error message disappears** (if any)
3. **"Select Folder" button appears**
4. **App is ready to use!**

---

## Using the App

1. Click **"Select Folder"**
2. Choose a folder with fish images (.jpg or .png)
3. Click **"Analyze Images"**
4. See keypoints and results
5. Click **"Export"** buttons to save CSV/JSON/PNG

---

## Important Notes

### ✅ Normal Things You'll See

- Terminal 1: `"GET /model/info HTTP/1.1" 200 OK` ← This is good!
- Terminal 2: `Watching for changes...` ← This is normal!
- Terminal 2: `Finished dev profile` ← App is ready!

### ❌ Things That Mean Something's Wrong

- Terminal 1 is closed/not running ← **Restart it!**
- Terminal 2 shows red errors ← **Let it auto-reload**
- Desktop app says "Connection Error" ← **Is Terminal 1 still running?**

### ℹ️ About `source ~/.cargo/env`

- It silently loads Rust environment
- No output = success (this is normal)
- Just run it and continue

---

## If Something Doesn't Work

### "App won't open"
- Check Terminal 1: `python3 -m backend.api.cli --port 8008` (must be running)
- Check Terminal 2: Any red errors?
- Restart: Close both, run again

### "Backend error" in app
- Terminal 1 backend must be running
- Don't press CTRL+C in Terminal 1!

### "Port 8008 already in use"
```bash
# Use a different port:
python3 -m backend.api.cli --port 9999
```

---

## The Two-Terminal System

```
Terminal 1 (NEVER CLOSE THIS)
├─ python3 -m backend.api.cli --port 8008
├─ Listens for requests
├─ Runs inference
└─ Returns results

Terminal 2 (Your GUI App)
├─ cargo tauri dev
├─ Opens desktop window
├─ Sends requests to Terminal 1
└─ Shows results to you
```

**Both must run together!**

---

## Quick Checklist

- [ ] Conda env activated: `conda activate cavfish310`
- [ ] Terminal 1 running backend
- [ ] Terminal 1 shows `Uvicorn running on http://127.0.0.1:8008`
- [ ] Terminal 2 running Tauri
- [ ] Desktop window opened
- [ ] Error message disappeared
- [ ] "Select Folder" button visible
- [ ] Ready to analyze!

---

## That's It!

Once both terminals are running, the app is ready to use.

Just pick a folder with fish images and click analyze! 🐠

