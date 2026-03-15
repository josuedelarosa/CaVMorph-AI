#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::{AppHandle, Manager};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

// ============================================================================
// Constants
// ============================================================================

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

fn apply_windows_no_window(cmd: &mut Command) {
    #[cfg(target_os = "windows")]
    {
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
}

fn default_python_command() -> &'static str {
    #[cfg(target_os = "windows")]
    { return "python"; }
    #[cfg(not(target_os = "windows"))]
    { return "python3"; }
}

/// Resolve bundled/portable Python from app data or Tauri resources.
fn bundled_python_candidates() -> Vec<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();

    // ── App-data managed copy ──
    let app_data = get_app_data_dir();
    #[cfg(target_os = "windows")]
    {
        candidates.push(app_data.join("python").join("python.exe"));
    }
    #[cfg(not(target_os = "windows"))]
    {
        candidates.push(app_data.join("python").join("bin").join("python3"));
        candidates.push(app_data.join("python").join("bin").join("python"));
    }

    // ── Tauri resource dir (installed builds) ──
    if let Some(rd) = get_resource_dir() {
        let prefixes: Vec<PathBuf> = vec![
            rd.join("runtime").join("python"),
            rd.join("_up_").join("runtime").join("python"),
            rd.join("python"),
            rd.join("_up_").join("python"),
        ];

        for base in prefixes {
            #[cfg(target_os = "windows")]
            {
                candidates.push(base.join("python.exe"));
            }
            #[cfg(not(target_os = "windows"))]
            {
                candidates.push(base.join("bin").join("python3"));
                candidates.push(base.join("bin").join("python"));
            }
        }
    }

    candidates.into_iter().filter(|p| p.exists()).collect()
}

// ============================================================================
// State & Types
// ============================================================================

struct AppState {
    backend_process: Mutex<Option<Child>>,
    backend_url: Mutex<String>,
    setup_complete: Mutex<bool>,
}

#[derive(Clone, serde::Serialize)]
struct SetupProgressEvent {
    step: u32,
    message: String,
    level: String,
}

#[derive(Clone, serde::Serialize)]
struct SetupCompleteEvent {
    success: bool,
    message: String,
}

// ============================================================================
// Path Helpers
// ============================================================================

fn get_app_data_dir() -> PathBuf {
    #[cfg(target_os = "macos")]
    {
        dirs::home_dir()
            .unwrap_or_default()
            .join(".phenoai")
    }
    #[cfg(target_os = "windows")]
    {
        dirs::config_dir()
            .unwrap_or_default()
            .join("PhenoAI")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        dirs::home_dir()
            .unwrap_or_default()
            .join(".local")
            .join("share")
            .join("phenoai")
    }
}

fn get_resource_dir() -> Option<PathBuf> {
    if let Ok(exe) = std::env::current_exe() {
        #[cfg(target_os = "macos")]
        {
            if let Some(resources) = exe.parent().and_then(|p| p.parent()).map(|p| p.join("Resources")) {
                if resources.exists() {
                    return Some(resources);
                }
            }
        }

        if let Some(parent) = exe.parent() {
            let candidate = parent.join("resources");
            if candidate.exists() {
                return Some(candidate);
            }
            if parent.exists() {
                return Some(parent.to_path_buf());
            }
        }
    }
    None
}

fn append_launcher_log(message: &str) {
    let logs_dir = get_app_data_dir().join("logs");
    let _ = fs::create_dir_all(&logs_dir);
    let log_path = logs_dir.join("launcher.log");

    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);

    if let Ok(mut file) = fs::OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(file, "[{}] {}", ts, message);
    }
}

/// Check if setup is complete (ONNX runtime + model + Python with packages)
fn is_setup_complete() -> bool {
    if let Some((_runtime_dir, model_dir)) = is_onnx_runtime_available() {
        for python_path in iter_python_candidates() {
            let check_script = r#"
import sys
try:
    import onnxruntime, numpy, cv2, fastapi, uvicorn, pydantic
    print("OK")
except ImportError as e:
    print(f"MISSING: {e}")
    sys.exit(1)
"#;
            let mut cmd = Command::new(&python_path);
            apply_windows_no_window(&mut cmd);
            if let Ok(output) = cmd.arg("-c").arg(check_script).output() {
                let stdout = String::from_utf8_lossy(&output.stdout);
                if output.status.success() && stdout.contains("OK") {
                    eprintln!("[is_setup_complete] ONNX runtime ready (python={:?}, model={:?})", python_path, model_dir);
                    return true;
                }
                eprintln!("[is_setup_complete] packages missing with {:?}: {}", python_path, stdout.trim());
            }
        }
    }

    eprintln!("[is_setup_complete] Setup NOT complete");
    false
}

/// Yield all Python candidates: env var → bundled → venv → system → py launcher.
fn iter_python_candidates() -> Vec<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();

    // 1) PHENOAI_PYTHON env override
    if let Ok(p) = env::var("PHENOAI_PYTHON") {
        let path = PathBuf::from(&p);
        if path.exists() { candidates.push(path); }
    }

    // 2) Bundled/portable Python runtime (highest priority for installed apps)
    for p in bundled_python_candidates() {
        if !candidates.iter().any(|c| c == &p) {
            candidates.push(p);
        }
    }

    // 3) App-local venv
    let app_data = get_app_data_dir();
    #[cfg(target_os = "windows")]
    {
        let p = app_data.join("venv").join("Scripts").join("python.exe");
        if p.exists() { candidates.push(p); }
    }
    #[cfg(not(target_os = "windows"))]
    {
        let p = app_data.join("venv").join("bin").join("python");
        if p.exists() { candidates.push(p); }
    }

    // 4) System python
    {
        let sys_cmd = default_python_command();
        let mut cmd = Command::new(sys_cmd);
        apply_windows_no_window(&mut cmd);
        if let Ok(output) = cmd.arg("--version").output() {
            if output.status.success() { candidates.push(PathBuf::from(sys_cmd)); }
        }
    }

    // 5) Windows py launcher
    #[cfg(target_os = "windows")]
    {
        for flag in &["-3.12", "-3.11", "-3.10", "-3"] {
            let mut cmd = Command::new("py");
            apply_windows_no_window(&mut cmd);
            if let Ok(output) = cmd.arg(flag).arg("--version").output() {
                if output.status.success() {
                    let mut resolve = Command::new("py");
                    apply_windows_no_window(&mut resolve);
                    if let Ok(out) = resolve.arg(flag).arg("-c").arg("import sys;print(sys.executable)").output() {
                        let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
                        if !s.is_empty() {
                            let p = PathBuf::from(&s);
                            if p.exists() && !candidates.iter().any(|c| c == &p) { candidates.push(p); }
                        }
                    }
                }
            }
        }
    }

    candidates
}

/// Resolve model directory (must contain model.onnx)
fn resolve_model_dir() -> Option<PathBuf> {
    let has_model = |dir: &Path| -> bool {
        dir.join("model.onnx").exists()
    };

    let app_data_models = get_app_data_dir().join("models").join("cavfish_v1");
    if has_model(&app_data_models) {
        return Some(app_data_models);
    }

    if let Some(home) = dirs::home_dir() {
        let old_models = home.join(".FishMorph").join("models").join("cavfish_v1");
        if has_model(&old_models) {
            return Some(old_models);
        }
    }

    if let Some(resource_dir) = get_resource_dir() {
        let bundled_models = resource_dir.join("models").join("cavfish_v1");
        if has_model(&bundled_models) {
            return Some(bundled_models);
        }

        let nested_models = resource_dir.join("_up_").join("_up_").join("models").join("cavfish_v1");
        if has_model(&nested_models) {
            return Some(nested_models);
        }
    }

    if let Ok(cwd) = env::current_dir() {
        let dev_candidates = [
            cwd.join("models").join("cavfish_v1"),
            cwd.join("..").join("models").join("cavfish_v1"),
            cwd.join("..").join("..").join("models").join("cavfish_v1"),
        ];

        for dev_models in dev_candidates {
            if has_model(&dev_models) {
                return Some(dev_models);
            }
        }
    }

    None
}

// ============================================================================
// Backend Process Management
// ============================================================================

fn find_free_port() -> Result<u16, String> {
    TcpListener::bind("127.0.0.1:0")
        .map_err(|e| format!("Failed to bind port: {}", e))
        .and_then(|listener| {
            listener
                .local_addr()
                .map_err(|e| format!("Failed to get local address: {}", e))
                .map(|addr| addr.port())
        })
}

/// Check if the ONNX runtime is available (model.onnx + inference_runtime/)
fn is_onnx_runtime_available() -> Option<(PathBuf, PathBuf)> {
    let model_dir = resolve_model_dir()?;
    let onnx_path = model_dir.join("model.onnx");
    let meta_path = model_dir.join("model_metadata.json");

    if !onnx_path.exists() || !meta_path.exists() {
        eprintln!("[is_onnx_runtime_available] model missing: onnx={} meta={}", onnx_path.exists(), meta_path.exists());
        return None;
    }

    let runtime_dir = resolve_inference_runtime_dir()?;
    let server_script = runtime_dir.join("runtime_server.py");
    if !server_script.exists() {
        eprintln!("[is_onnx_runtime_available] runtime_server.py not found in {:?}", runtime_dir);
        return None;
    }

    eprintln!("[is_onnx_runtime_available] OK: runtime={:?}, model={:?}", runtime_dir, model_dir);
    Some((runtime_dir, model_dir))
}

/// Resolve inference_runtime directory
fn resolve_inference_runtime_dir() -> Option<PathBuf> {
    let app_data_runtime = get_app_data_dir().join("inference_runtime");
    if app_data_runtime.exists() {
        return Some(app_data_runtime);
    }

    if let Some(resource_dir) = get_resource_dir() {
        let bundled_runtime = resource_dir.join("inference_runtime");
        if bundled_runtime.exists() {
            return Some(bundled_runtime);
        }

        // Tauri rewrites ../../ → _up_/_up_/
        let nested_runtime = resource_dir.join("_up_").join("_up_").join("inference_runtime");
        if nested_runtime.exists() {
            return Some(nested_runtime);
        }
    }

    if let Ok(cwd) = env::current_dir() {
        let dev_runtime = cwd.join("inference_runtime");
        if dev_runtime.exists() {
            return Some(dev_runtime);
        }
        let parent_runtime = cwd.join("..").join("inference_runtime");
        if parent_runtime.exists() {
            return Some(parent_runtime);
        }
    }

    None
}

/// Find a Python interpreter that has ONNX packages installed.
fn find_runtime_python() -> Option<PathBuf> {
    let check = r#"import onnxruntime,numpy,cv2,fastapi,uvicorn;print('OK')"#;
    for p in iter_python_candidates() {
        let mut cmd = Command::new(&p);
        apply_windows_no_window(&mut cmd);
        if let Ok(output) = cmd.arg("-c").arg(check).output() {
            if output.status.success() && String::from_utf8_lossy(&output.stdout).contains("OK") {
                eprintln!("[find_runtime_python] Found Python with ONNX packages: {:?}", p);
                return Some(p);
            }
        }
    }
    // Fallback: any working Python (setup will install packages)
    for p in iter_python_candidates() {
        let mut cmd = Command::new(&p);
        apply_windows_no_window(&mut cmd);
        if let Ok(output) = cmd.arg("--version").output() {
            if output.status.success() {
                eprintln!("[find_runtime_python] Fallback Python (no ONNX packages): {:?}", p);
                return Some(p);
            }
        }
    }
    None
}

/// Spawn the ONNX inference runtime backend server.
fn spawn_backend(port: u16) -> Result<(Child, String), String> {
    let (runtime_dir, model_dir) = is_onnx_runtime_available()
        .ok_or_else(|| "ONNX runtime not available (model or inference_runtime missing)".to_string())?;

    let python_path = find_runtime_python()
        .ok_or_else(|| "No Python interpreter found with required packages".to_string())?;

    eprintln!("[spawn_backend] Python: {:?}", python_path);
    eprintln!("[spawn_backend] Runtime dir: {:?}", runtime_dir);
    eprintln!("[spawn_backend] Model dir: {:?}", model_dir);

    let app_data_dir = get_app_data_dir();
    let logs_dir = app_data_dir.join("logs");
    let _ = fs::create_dir_all(&logs_dir);
    let backend_log_path = logs_dir.join("backend.log");

    let runtime_parent = runtime_dir.parent().unwrap_or(&runtime_dir);
    let startup_script = format!(
        r#"
import sys, os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
sys.path.insert(0, '{}')
os.environ['FISH_MODEL_DIR'] = '{}'
os.environ['FISH_PORT'] = '{}'
os.environ['FISH_DEVICE'] = 'cpu'
from inference_runtime.runtime_server import app
import uvicorn
uvicorn.run(app, host='127.0.0.1', port={}, log_level='info')
"#,
        runtime_parent.to_string_lossy().replace('\\', "\\\\").replace('\'', "\\'"),
        model_dir.to_string_lossy().replace('\\', "\\\\").replace('\'', "\\'"),
        port,
        port,
    );

    let mut cmd = Command::new(&python_path);
    apply_windows_no_window(&mut cmd);
    cmd.arg("-c");
    cmd.arg(&startup_script);
    cmd.env("FISH_PORT", port.to_string());
    cmd.env("FISH_DEVICE", "cpu");
    cmd.env("FISH_MODEL_DIR", model_dir.to_string_lossy().to_string());
    cmd.env("KMP_DUPLICATE_LIB_OK", "TRUE");
    cmd.env("PYTHONDONTWRITEBYTECODE", "1");

    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Failed to spawn backend: {}", e))?;

    eprintln!("[spawn_backend] PID: {:?}", child.id());
    let base_url = format!("http://127.0.0.1:{}", port);

    // Capture stderr
    let stderr_log_path = backend_log_path.clone();
    if let Some(stderr) = child.stderr.take() {
        thread::spawn(move || {
            let reader = BufReader::new(stderr);
            for line in reader.lines().flatten() {
                eprintln!("[backend stderr] {}", line);
                if let Ok(mut file) = fs::OpenOptions::new().create(true).append(true).open(&stderr_log_path) {
                    let _ = writeln!(file, "[stderr] {}", line);
                }
            }
        });
    }
    // Capture stdout
    let stdout_log_path = backend_log_path;
    if let Some(stdout) = child.stdout.take() {
        thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines().flatten() {
                eprintln!("[backend stdout] {}", line);
                if let Ok(mut file) = fs::OpenOptions::new().create(true).append(true).open(&stdout_log_path) {
                    let _ = writeln!(file, "[stdout] {}", line);
                }
            }
        });
    }

    // Wait for server ready
    let start = std::time::Instant::now();
    let timeout = Duration::from_secs(30);
    loop {
        if start.elapsed() > timeout {
            let _ = child.kill();
            return Err("Backend startup timeout (30s)".to_string());
        }
        if let Ok(Some(status)) = child.try_wait() {
            return Err(format!("Backend crashed on startup: {:?}", status));
        }
        if TcpListener::bind(format!("127.0.0.1:{}", port)).is_err() {
            eprintln!("[spawn_backend] Port {} ready!", port);
            return Ok((child, base_url));
        }
        thread::sleep(Duration::from_millis(200));
    }
}

// ============================================================================
// Tauri Commands
// ============================================================================

#[tauri::command]
fn get_backend_url(state: tauri::State<AppState>) -> String {
    state.backend_url.lock().unwrap().clone()
}

#[tauri::command]
async fn ensure_backend_running(state: tauri::State<'_, AppState>) -> Result<String, String> {
    append_launcher_log("ensure_backend_running: invoked");

    // Fast path: backend URL already set and process appears alive.
    {
        let existing_url = state.backend_url.lock().unwrap().clone();
        if !existing_url.is_empty() {
            let mut guard = state.backend_process.lock().unwrap();
            if let Some(child) = guard.as_mut() {
                if child.try_wait().ok().flatten().is_none() {
                    append_launcher_log(&format!("ensure_backend_running: reusing existing backend {}", existing_url));
                    return Ok(existing_url);
                }
            }
        }
    }

    // Start or restart backend.
    let port = find_free_port().unwrap_or(8008);
    append_launcher_log(&format!("ensure_backend_running: starting backend on port {}", port));
    match spawn_backend(port) {
        Ok((child, url)) => {
            *state.backend_process.lock().unwrap() = Some(child);
            *state.backend_url.lock().unwrap() = url.clone();
            *state.setup_complete.lock().unwrap() = true;
            append_launcher_log(&format!("ensure_backend_running: backend started {}", url));
            Ok(url)
        }
        Err(e) => {
            append_launcher_log(&format!("ensure_backend_running: failed: {}", e));
            Err(format!("Failed to ensure backend running: {}", e))
        }
    }
}

#[tauri::command]
fn check_setup_needed() -> bool {
    let needed = !is_setup_complete();
    append_launcher_log(&format!("check_setup_needed: {}", needed));
    needed
}

/// Return the path to a usable Python interpreter, or an error.
#[tauri::command]
fn check_python_installed() -> Result<String, String> {
    if let Some(p) = find_runtime_python() {
        return Ok(p.to_string_lossy().to_string());
    }
    Err("Python not found. Please install Python 3.9 or later.".to_string())
}

/// Check whether the ONNX pip dependencies are importable.
#[tauri::command]
fn check_onnx_dependencies() -> Result<bool, String> {
    let check = r#"import onnxruntime,numpy,cv2,fastapi,uvicorn;print('OK')"#;
    for p in iter_python_candidates() {
        let mut cmd = Command::new(&p);
        apply_windows_no_window(&mut cmd);
        if let Ok(output) = cmd.arg("-c").arg(check).output() {
            if output.status.success() && String::from_utf8_lossy(&output.stdout).contains("OK") {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

/// Check if the ONNX model file exists and return its location.
#[tauri::command]
fn check_model_available() -> Result<String, String> {
    if let Some(model_dir) = resolve_model_dir() {
        if model_dir.join("model.onnx").exists() && model_dir.join("model_metadata.json").exists() {
            return Ok(model_dir.to_string_lossy().to_string());
        }
    }
    Err("model.onnx or model_metadata.json not found".to_string())
}

#[tauri::command]
async fn run_first_time_setup(app: AppHandle) -> Result<(), String> {
    let setup_script = if cfg!(debug_assertions) {
        PathBuf::from("desktop/setup_onnx_runtime.py")
    } else {
        app.path_resolver()
            .resolve_resource("setup_onnx_runtime.py")
            .or_else(|| app.path_resolver().resolve_resource("_up_/setup_onnx_runtime.py"))
            .ok_or_else(|| "Setup script not found in resources".to_string())?
    };

    let python = find_runtime_python()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|| default_python_command().to_string());

    let app_data_dir = get_app_data_dir();
    let model_dir = resolve_model_dir().unwrap_or_else(|| app_data_dir.join("models").join("cavfish_v1"));

    eprintln!("[run_first_time_setup] script={:?}  python={}  model_dir={:?}", setup_script, python, model_dir);

    let mut cmd = Command::new(&python);
    apply_windows_no_window(&mut cmd);
    cmd.arg(&setup_script);
    cmd.arg("--app-data-dir").arg(&app_data_dir);
    cmd.arg("--model-dir").arg(&model_dir);

    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Failed to start setup: {}", e))?;

    let stdout = child.stdout.take().ok_or("Failed to capture stdout")?;
    let stderr = child.stderr.take().ok_or("Failed to capture stderr")?;

    let stdout_app = app.clone();
    thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines().flatten() {
            if let Ok(json) = serde_json::from_str::<serde_json::Value>(&line) {
                if let Some(msg_type) = json.get("type").and_then(|v| v.as_str()) {
                    match msg_type {
                        "progress" => {
                            let event = SetupProgressEvent {
                                step: json.get("step").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
                                message: json.get("message").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                                level: json.get("level").and_then(|v| v.as_str()).unwrap_or("info").to_string(),
                            };
                            let _ = stdout_app.emit_all("setup-progress", event);
                        }
                        "complete" => {
                            let event = SetupCompleteEvent {
                                success: true,
                                message: "Setup completed successfully".to_string(),
                            };
                            let _ = stdout_app.emit_all("setup-complete", event);
                        }
                        "error" => {
                            let message = json.get("message").and_then(|v| v.as_str()).unwrap_or("Unknown error").to_string();
                            let _ = stdout_app.emit_all("setup-error", message);
                        }
                        _ => {}
                    }
                }
            } else {
                let event = SetupProgressEvent {
                    step: 0,
                    message: line,
                    level: "info".to_string(),
                };
                let _ = stdout_app.emit_all("setup-progress", event);
            }
        }
    });

    thread::spawn(move || {
        let reader = BufReader::new(stderr);
        for line in reader.lines().flatten() {
            eprintln!("[setup stderr] {}", line);
        }
    });

    let status = child.wait().map_err(|e| format!("Setup process error: {}", e))?;

    if status.success() {
        Ok(())
    } else {
        Err(format!("Setup failed with exit code: {:?}", status.code()))
    }
}

#[tauri::command]
fn open_setup_logs() -> Result<(), String> {
    let logs_dir = get_app_data_dir().join("logs");
    fs::create_dir_all(&logs_dir).ok();

    #[cfg(target_os = "macos")]
    {
        Command::new("open").arg(&logs_dir).spawn()
            .map_err(|e| format!("Failed to open logs: {}", e))?;
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("explorer").arg(&logs_dir).spawn()
            .map_err(|e| format!("Failed to open logs: {}", e))?;
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open").arg(&logs_dir).spawn()
            .map_err(|e| format!("Failed to open logs: {}", e))?;
    }

    Ok(())
}

#[tauri::command]
async fn finish_setup_and_start(state: tauri::State<'_, AppState>) -> Result<String, String> {
    append_launcher_log("finish_setup_and_start: invoked");
    eprintln!("[finish_setup_and_start] Starting backend server...");

    let port = find_free_port().unwrap_or(8008);
    eprintln!("[finish_setup_and_start] Port: {}", port);

    match spawn_backend(port) {
        Ok((child, url)) => {
            eprintln!("[finish_setup_and_start] Backend started at {}", url);
            *state.backend_process.lock().unwrap() = Some(child);
            *state.backend_url.lock().unwrap() = url.clone();
            *state.setup_complete.lock().unwrap() = true;
            append_launcher_log(&format!("finish_setup_and_start: started {}", url));
            Ok(url)
        }
        Err(e) => {
            eprintln!("[finish_setup_and_start] Failed: {}", e);
            append_launcher_log(&format!("finish_setup_and_start: failed: {}", e));
            Err(format!("Failed to start backend: {}", e))
        }
    }
}

#[tauri::command]
fn get_app_data_path() -> String {
    get_app_data_dir().to_string_lossy().to_string()
}

// ============================================================================
// Main
// ============================================================================

fn main() {
    let app_state = AppState {
        backend_process: Mutex::new(None),
        backend_url: Mutex::new(String::new()),
        setup_complete: Mutex::new(false),
    };

    tauri::Builder::default()
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            get_backend_url,
            ensure_backend_running,
            check_setup_needed,
            check_python_installed,
            check_onnx_dependencies,
            check_model_available,
            run_first_time_setup,
            open_setup_logs,
            finish_setup_and_start,
            get_app_data_path
        ])
        .setup(|app| {
            let setup_needed = !is_setup_complete();

            if !setup_needed {
                if let Ok(port) = find_free_port() {
                    if let Ok((child, url)) = spawn_backend(port) {
                        let state = app.state::<AppState>();
                        *state.backend_process.lock().unwrap() = Some(child);
                        *state.backend_url.lock().unwrap() = url;
                        *state.setup_complete.lock().unwrap() = true;
                    }
                }
            }

            Ok(())
        })
        .on_window_event(|event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event.event() {
                let state = event.window().state::<AppState>();
                let mut guard = state.backend_process.lock().unwrap();
                if let Some(ref mut child) = *guard {
                    let _ = child.kill();
                }
                *guard = None;
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

