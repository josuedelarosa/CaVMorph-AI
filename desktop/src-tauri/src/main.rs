#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::{AppHandle, Manager};

// ============================================================================
// Constants
// ============================================================================

const CONDA_ENV_NAME: &str = "cavfish310";

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

/// Get application data directory
fn get_app_data_dir() -> PathBuf {
    #[cfg(target_os = "macos")]
    {
        // Use hidden folder to avoid spaces in path (Miniforge installer issue)
        dirs::home_dir()
            .unwrap_or_default()
            .join(".MorphologIA")
    }
    #[cfg(target_os = "windows")]
    {
        dirs::config_dir()
            .unwrap_or_default()
            .join("MorphologIA")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        dirs::home_dir()
            .unwrap_or_default()
            .join(".local")
            .join("share")
            .join("MorphologIA")
    }
}

/// Best-effort resource directory lookup (works for macOS app bundles)
fn get_resource_dir() -> Option<PathBuf> {
    if let Ok(exe) = std::env::current_exe() {
        #[cfg(target_os = "macos")]
        {
            // .../Contents/MacOS/<app> -> .../Contents/Resources
            if let Some(resources) = exe.parent().and_then(|p| p.parent()).map(|p| p.join("Resources")) {
                if resources.exists() {
                    return Some(resources);
                }
            }
        }

        // Fallbacks for other platforms
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

/// Find conda executable
fn find_conda() -> Option<PathBuf> {
    // First check app-managed conda
    let app_conda = get_app_data_dir().join("conda/bin/conda");
    if app_conda.exists() {
        return Some(app_conda);
    }
    
    // Fallback to system conda
    let home = dirs::home_dir()?;
    
    let candidates = [
        home.join("miniforge3/bin/conda"),
        home.join("mambaforge/bin/conda"),
        home.join("miniconda3/bin/conda"),
        home.join("anaconda3/bin/conda"),
        PathBuf::from("/opt/homebrew/Caskroom/miniforge/base/bin/conda"),
        PathBuf::from("/usr/local/Caskroom/miniforge/base/bin/conda"),
    ];
    
    for path in &candidates {
        if path.exists() {
            return Some(path.clone());
        }
    }
    
    // Try which conda
    if let Ok(output) = Command::new("which").arg("conda").output() {
        if output.status.success() {
            let path_str = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !path_str.is_empty() {
                return Some(PathBuf::from(path_str));
            }
        }
    }
    
    None
}

/// Check if setup is complete
fn is_setup_complete() -> bool {
    let config_path = get_app_data_dir().join("config.json");
    if config_path.exists() {
        if let Ok(content) = fs::read_to_string(&config_path) {
            if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                let setup_complete = json.get("setup_complete").and_then(|v| v.as_bool()).unwrap_or(false);
                if !setup_complete {
                    return false;
                }
            }
        }
    }
    
    // Check if conda env exists and has required packages
    let python_path = match get_python_path() {
        Some(p) => p,
        None => {
            eprintln!("[is_setup_complete] Python not found in conda environment");
            return false;
        }
    };
    
    // CRITICAL: Verify that required packages are actually installed
    let check_script = r#"
import sys
try:
    import torch
    import mmpose
    import mmengine
    import mmcv
    import mmdet
    import fastapi
    import uvicorn
    import cv2
    print("OK")
except ImportError as e:
    print(f"MISSING: {e}")
    sys.exit(1)
"#;
    
    if let Ok(output) = Command::new(&python_path)
        .arg("-c")
        .arg(check_script)
        .output()
    {
        let stdout = String::from_utf8_lossy(&output.stdout);
        if !output.status.success() || !stdout.contains("OK") {
            eprintln!("[is_setup_complete] Required packages not installed: {}", stdout);
            return false;
        }
    } else {
        eprintln!("[is_setup_complete] Failed to run package verification");
        return false;
    }
    
    // CRITICAL: Check if model weights exist
    let weights_path = get_app_data_dir()
        .join("models")
        .join("cavfish_v1")
        .join("weights.pth");
    
    if !weights_path.exists() {
        eprintln!("[is_setup_complete] Model weights not found at: {:?}", weights_path);
        return false;
    }
    
    // Verify weights file is not empty
    if let Ok(metadata) = fs::metadata(&weights_path) {
        if metadata.len() < 1_000_000 {  // weights.pth should be ~1GB
            eprintln!("[is_setup_complete] Weights file too small: {} bytes", metadata.len());
            return false;
        }
    } else {
        return false;
    }
    
    true
}

/// Get Python executable from conda env
fn get_python_path() -> Option<PathBuf> {
    let conda_path = find_conda()?;
    
    // First, try parsing conda env list to find the actual path
    if let Ok(output) = Command::new(&conda_path)
        .args(&["env", "list"])
        .output()
    {
        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                if line.contains(CONDA_ENV_NAME) && !line.trim().starts_with('#') {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    // Find the path (last part that contains '/')
                    for part in parts.iter().rev() {
                        if part.contains('/') && part.contains(CONDA_ENV_NAME) {
                            let env_path = PathBuf::from(part);
                            let python_path = env_path.join("bin").join("python");
                            if python_path.exists() {
                                return Some(python_path);
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Fallback: check common conda environment locations
    let home = dirs::home_dir()?;
    let conda_base = conda_path.parent()?.parent()?;
    let app_data = get_app_data_dir();
    
    let candidates = [
        app_data.join("conda/envs").join(CONDA_ENV_NAME).join("bin/python"),
        home.join(".conda/envs").join(CONDA_ENV_NAME).join("bin/python"),
        conda_base.join("envs").join(CONDA_ENV_NAME).join("bin/python"),
        home.join("miniforge3/envs").join(CONDA_ENV_NAME).join("bin/python"),
        home.join("mambaforge/envs").join(CONDA_ENV_NAME).join("bin/python"),
        home.join("miniconda3/envs").join(CONDA_ENV_NAME).join("bin/python"),
        home.join("anaconda3/envs").join(CONDA_ENV_NAME).join("bin/python"),
    ];
    
    for path in &candidates {
        if path.exists() {
            return Some(path.clone());
        }
    }
    
    None
}

/// Resolve backend source directory (app data, bundled resources, or dev repo)
fn resolve_backend_dir() -> Option<PathBuf> {
    if let Ok(custom) = env::var("FISH_BACKEND_DIR") {
        let path = PathBuf::from(custom);
        if path.exists() {
            return Some(path);
        }
    }

    let app_data_backend = get_app_data_dir().join("backend");
    if app_data_backend.exists() {
        return Some(app_data_backend);
    }

    if let Some(resource_dir) = get_resource_dir() {
        let bundled_backend = resource_dir.join("backend");
        if bundled_backend.exists() {
            return Some(bundled_backend);
        }

        // Tauri resource paths for ../../backend
        let nested_backend = resource_dir.join("_up_").join("_up_").join("backend");
        if nested_backend.exists() {
            return Some(nested_backend);
        }
    }

    // Development fallback: repo root contains backend/
    if let Ok(cwd) = env::current_dir() {
        let dev_backend = cwd.join("backend");
        if dev_backend.exists() {
            return Some(dev_backend);
        }
    }

    None
}

/// Resolve model directory (prefers app data, else bundled resources, else dev repo)
fn resolve_model_dir() -> Option<PathBuf> {
    let app_data_models = get_app_data_dir().join("models").join("cavfish_v1");
    if app_data_models.exists() {
        return Some(app_data_models);
    }

    if let Some(resource_dir) = get_resource_dir() {
        let bundled_models = resource_dir.join("models").join("cavfish_v1");
        if bundled_models.exists() {
            return Some(bundled_models);
        }

        let nested_models = resource_dir.join("_up_").join("_up_").join("models").join("cavfish_v1");
        if nested_models.exists() {
            return Some(nested_models);
        }
    }

    if let Ok(cwd) = env::current_dir() {
        let dev_models = cwd.join("models").join("cavfish_v1");
        if dev_models.exists() {
            return Some(dev_models);
        }
    }

    None
}

/// Ensure model files are available in app data if bundled files exist
fn ensure_model_weights_in_app_data() {
    let app_data_models = get_app_data_dir().join("models").join("cavfish_v1");
    let _ = fs::create_dir_all(&app_data_models);
    
    eprintln!("[ensure_model_weights] App data models dir: {:?}", app_data_models);
    
    // Check if weights already exist in app data
    let app_data_weights = app_data_models.join("weights.pth");
    if app_data_weights.exists() {
        if let Ok(metadata) = fs::metadata(&app_data_weights) {
            eprintln!("[ensure_model_weights] Weights already in app data ({} MB)", metadata.len() / 1024 / 1024);
            return;
        }
    }
    
    if let Some(resource_dir) = get_resource_dir() {
        eprintln!("[ensure_model_weights] Resource dir: {:?}", resource_dir);
        
        // Try multiple possible paths for bundled models
        let possible_paths = vec![
            resource_dir.join("models").join("cavfish_v1"),  // Direct path
            resource_dir.join("_up_").join("_up_").join("models").join("cavfish_v1"),  // ../../models/
            resource_dir.join(".." ).join("..").join("models").join("cavfish_v1"),  // Actual parent dirs
        ];
        
        // Debug: List contents of resource_dir
        if let Ok(entries) = fs::read_dir(&resource_dir) {
            eprintln!("[ensure_model_weights] Resource dir contents:");
            for entry in entries.take(10) {
                if let Ok(entry) = entry {
                    eprintln!("  - {:?}", entry.file_name());
                }
            }
        }
        
        for bundled_models in possible_paths {
            eprintln!("[ensure_model_weights] Checking: {:?}", bundled_models);
            
            if bundled_models.exists() {
                eprintln!("[ensure_model_weights] Found bundled models at: {:?}", bundled_models);
                
                // Copy config files
                for name in ["meta.json", "config.py", "config_infer.py"] {
                    let src = bundled_models.join(name);
                    let dest = app_data_models.join(name);
                    if src.exists() && !dest.exists() {
                        if let Ok(_) = fs::copy(&src, &dest) {
                            eprintln!("[ensure_model_weights] Copied {}", name);
                        }
                    }
                }
                
                // Copy model weights
                let bundled_weights = bundled_models.join("weights.pth");
                if bundled_weights.exists() {
                    if let Ok(metadata) = fs::metadata(&bundled_weights) {
                        eprintln!("[ensure_model_weights] Found weights.pth ({} MB)", metadata.len() / 1024 / 1024);
                    }
                    eprintln!("[ensure_model_weights] Copying weights to app data...");
                    
                    if let Err(err) = fs::copy(&bundled_weights, &app_data_weights) {
                        eprintln!("[ensure_model_weights] Failed to copy: {}", err);
                    } else {
                        eprintln!("[ensure_model_weights] ✅ Weights copied successfully");
                        return;  // Success!
                    }
                } else {
                    eprintln!("[ensure_model_weights] weights.pth not at: {:?}", bundled_weights);
                }
            }
        }
        
        eprintln!("[ensure_model_weights] ⚠️ Could not find bundled weights in any expected location");
    } else {
        eprintln!("[ensure_model_weights] Resource directory not found");
    }
}

// ============================================================================
// Backend Process Management
// ============================================================================

/// Find a free port by binding to port 0
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

/// Spawn backend process using conda environment
fn spawn_backend(port: u16) -> Result<(Child, String), String> {
    let python_path = get_python_path()
        .ok_or_else(|| "Python not found in conda environment".to_string())?;
    
    eprintln!("[spawn_backend] Python path: {:?}", python_path);
    
    ensure_model_weights_in_app_data();
    let app_data_dir = get_app_data_dir();
    let backend_dir = resolve_backend_dir();
    let models_dir = resolve_model_dir();
    let logs_dir = app_data_dir.join("logs");
    let _ = fs::create_dir_all(&logs_dir);
    let backend_log_path = logs_dir.join("backend.log");
    
    // Create cache directories outside .app bundle to prevent AMFI violations
    let home_dir = dirs::home_dir().ok_or("Cannot determine home directory")?;
    let cache_base = home_dir.join("Library/Caches/MorphologIA");
    let pycache_dir = cache_base.join("pycache");
    let torch_cache = cache_base.join("torch");
    let mpl_cache = cache_base.join("matplotlib");
    
    // Create all cache directories
    let _ = fs::create_dir_all(&pycache_dir);
    let _ = fs::create_dir_all(&torch_cache);
    let _ = fs::create_dir_all(&mpl_cache);
    
    eprintln!("[spawn_backend] App data dir: {:?}", app_data_dir);
    eprintln!("[spawn_backend] Backend dir: {:?}", backend_dir);
    eprintln!("[spawn_backend] Models dir: {:?}", models_dir);
    eprintln!("[spawn_backend] Cache dir: {:?}", cache_base);
    
    // Determine which backend module to use
    let mut cmd = Command::new(&python_path);
    
    if let Some(backend_dir) = &backend_dir {
        // Production: run from copied backend in app data
        // Create a startup script that properly escapes the path
        let backend_path = backend_dir.to_string_lossy().replace("'", "\\'");
        let startup_script = format!(
            r#"
import sys
import os

# Fix OpenMP duplicate library issue on macOS - MUST be set before importing torch/numpy
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

backend_path = '{}'
sys.path.insert(0, backend_path)
os.chdir(backend_path)
print(f'[startup] Python: {{sys.executable}}', flush=True)
print(f'[startup] Path: {{sys.path[:3]}}', flush=True)
print(f'[startup] Backend dir: {{backend_path}}', flush=True)
print(f'[startup] FISH_MODEL_DIR: {{os.environ.get("FISH_MODEL_DIR")}}', flush=True)
print(f'[startup] FISH_PORT: {{os.environ.get("FISH_PORT")}}', flush=True)
print(f'[startup] KMP_DUPLICATE_LIB_OK: {{os.environ.get("KMP_DUPLICATE_LIB_OK")}}', flush=True)
try:
    from api.app import app
    print('[startup] Successfully imported app', flush=True)
except Exception as e:
    print(f'[startup] Failed to import api.app: {{e}}', flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
import uvicorn
uvicorn.run(app, host='127.0.0.1', port={}, log_level='info')
"#,
            backend_path,
            port
        );
        eprintln!("[spawn_backend] Running inline startup script");
        cmd.arg("-c");
        cmd.arg(&startup_script);
    } else {
        // Fall back to development mode
        eprintln!("[spawn_backend] Development mode: -m backend.api.cli");
        cmd.args(["-m", "backend.api.cli"]);
    }
    
    cmd.env("FISH_PORT", port.to_string());
    // Force CPU since conda env has cpuonly PyTorch
    cmd.env("FISH_DEVICE", "cpu");
    if let Some(models_dir) = &models_dir {
        cmd.env("FISH_MODEL_DIR", models_dir.to_string_lossy().to_string());
    }
    
    // Fix OpenMP duplicate library issue on macOS
    cmd.env("KMP_DUPLICATE_LIB_OK", "TRUE");
    
    // AMFI fix: Disable Python bytecode generation and redirect all caches outside .app bundle
    cmd.env("PYTHONDONTWRITEBYTECODE", "1");
    cmd.env("PYTHONPYCACHEPREFIX", pycache_dir.to_string_lossy().to_string());
    cmd.env("XDG_CACHE_HOME", cache_base.to_string_lossy().to_string());
    cmd.env("TORCH_HOME", torch_cache.to_string_lossy().to_string());
    cmd.env("MPLCONFIGDIR", mpl_cache.to_string_lossy().to_string());
    
    eprintln!("[spawn_backend] Model dir: {:?}", models_dir);
    eprintln!("[spawn_backend] Port: {}", port);
    
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());
    
    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Failed to spawn backend: {}", e))?;
    
    eprintln!("[spawn_backend] Process spawned with PID: {:?}", child.id());
    
    let base_url = format!("http://127.0.0.1:{}", port);
    
    // Capture stderr for debugging - store in shared string
    let stderr_output = std::sync::Arc::new(std::sync::Mutex::new(String::new()));
    let stderr_output_clone = stderr_output.clone();
    let stderr_log_path = backend_log_path.clone();
    
    let stderr = child.stderr.take();
    let _stderr_thread = if let Some(stderr) = stderr {
        Some(thread::spawn(move || {
            let reader = BufReader::new(stderr);
            for line in reader.lines().flatten() {
                eprintln!("[backend stderr] {}", line);
                if let Ok(mut output) = stderr_output_clone.lock() {
                    output.push_str(&line);
                    output.push('\n');
                }
                if let Ok(mut file) = fs::OpenOptions::new().create(true).append(true).open(&stderr_log_path) {
                    let _ = writeln!(file, "[stderr] {}", line);
                }
            }
        }))
    } else {
        None
    };
    
    // Capture stdout for debugging - store in shared string
    let stdout_output = std::sync::Arc::new(std::sync::Mutex::new(String::new()));
    let stdout_output_clone = stdout_output.clone();
    let stdout_log_path = backend_log_path.clone();
    
    let stdout = child.stdout.take();
    let _stdout_thread = if let Some(stdout) = stdout {
        Some(thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines().flatten() {
                eprintln!("[backend stdout] {}", line);
                if let Ok(mut output) = stdout_output_clone.lock() {
                    output.push_str(&line);
                    output.push('\n');
                }
                if let Ok(mut file) = fs::OpenOptions::new().create(true).append(true).open(&stdout_log_path) {
                    let _ = writeln!(file, "[stdout] {}", line);
                }
            }
        }))
    } else {
        None
    };
    
    // Wait for server to be ready (simple polling)
    let start = std::time::Instant::now();
    let timeout = Duration::from_secs(60);
    
    loop {
        if start.elapsed() > timeout {
            eprintln!("[spawn_backend] Timeout after 60s waiting for port {}", port);
            // Try to kill the child process
            let _ = child.kill();
            return Err("Backend startup timeout (60s)".to_string());
        }
        
        // Check if child process has exited (crashed)
        if let Ok(Some(status)) = child.try_wait() {
            // Give threads a moment to capture output
            thread::sleep(Duration::from_millis(100));
            
            let stderr_str = stderr_output.lock().map(|s| s.clone()).unwrap_or_default();
            let stdout_str = stdout_output.lock().map(|s| s.clone()).unwrap_or_default();
            
            eprintln!("[spawn_backend] Child process exited with status: {:?}", status);
            eprintln!("[spawn_backend] Captured stdout:\n{}", stdout_str);
            eprintln!("[spawn_backend] Captured stderr:\n{}", stderr_str);
            
            // Return a more detailed error message
            let error_detail = if !stderr_str.is_empty() {
                stderr_str.lines().last().unwrap_or("Unknown error").to_string()
            } else if !stdout_str.is_empty() {
                stdout_str.lines().last().unwrap_or("Unknown error").to_string()
            } else {
                format!("Exit status: {:?}", status)
            };
            
            return Err(format!("Backend crashed: {}", error_detail));
        }
        
        // Check if port is in use (server is running)
        if TcpListener::bind(format!("127.0.0.1:{}", port)).is_err() {
            eprintln!("[spawn_backend] Port {} is now in use, server is ready!", port);
            return Ok((child, base_url));
        }
        
        if start.elapsed().as_secs() % 5 == 0 && start.elapsed().as_millis() % 5000 < 500 {
            eprintln!("[spawn_backend] Still waiting... {}s elapsed", start.elapsed().as_secs());
        }
        
        thread::sleep(Duration::from_millis(500));
    }
}

// ============================================================================
// Tauri Commands
// ============================================================================

/// Check if macOS Command Line Developer Tools are installed
#[tauri::command]
fn check_xcode_tools_installed() -> Result<bool, String> {
    #[cfg(target_os = "macos")]
    {
        // Check using xcode-select -p
        match Command::new("xcode-select")
            .arg("-p")
            .output()
        {
            Ok(output) => {
                if output.status.success() {
                    Ok(true)
                } else {
                    Ok(false)
                }
            }
            Err(_) => {
                // If xcode-select itself doesn't exist, tools aren't installed
                Ok(false)
            }
        }
    }
    #[cfg(not(target_os = "macos"))]
    {
        // On non-macOS, always return true (not applicable)
        Ok(true)
    }
}

#[tauri::command]
fn get_backend_url(state: tauri::State<AppState>) -> String {
    state.backend_url.lock().unwrap().clone()
}

#[tauri::command]
fn check_setup_needed() -> bool {
    !is_setup_complete()
}

#[tauri::command]
fn check_conda_installed() -> Result<String, String> {
    match find_conda() {
        Some(path) => Ok(path.to_string_lossy().to_string()),
        None => Err("Conda not found. Please install Miniforge first.".to_string()),
    }
}

#[tauri::command]
fn check_conda_env_exists() -> bool {
    if let Some(conda_path) = find_conda() {
        let conda_base = conda_path.parent().and_then(|p| p.parent());
        if let Some(base) = conda_base {
            let env_path = base.join("envs").join(CONDA_ENV_NAME);
            let python_path = env_path.join("bin").join("python");
            return python_path.exists();
        }
    }
    false
}

#[tauri::command]
async fn run_first_time_setup(app: AppHandle) -> Result<(), String> {
    // Get the setup script path
    let setup_script = if cfg!(debug_assertions) {
        // Development: use script from workspace
        PathBuf::from("desktop/setup_first_run.py")
    } else {
        // Production: extract from resources
        let resource_path = app.path_resolver()
            .resolve_resource("setup_first_run.py")
            .ok_or_else(|| "Setup script not found in resources".to_string())?;
        resource_path
    };
    
    // Get backend directory (source for copying)
    let backend_dir = if cfg!(debug_assertions) {
        env::current_dir().unwrap_or_default()
    } else {
        app.path_resolver()
            .resource_dir()
            .unwrap_or_default()
    };
    
    // Find Python to run setup script (system Python or from conda)
    let python = if let Some(env_python) = get_python_path() {
        env_python.to_string_lossy().to_string()
    } else if let Some(conda_path) = find_conda() {
        let conda_base = conda_path.parent().and_then(|p| p.parent());
        if let Some(base) = conda_base {
            let conda_python = base.join("bin").join("python");
            if conda_python.exists() {
                conda_python.to_string_lossy().to_string()
            } else {
                "python3".to_string()
            }
        } else {
            "python3".to_string()
        }
    } else {
        "python3".to_string()
    };
    
    // Spawn setup process
    let mut cmd = Command::new(&python);
    cmd.arg(&setup_script);
    cmd.arg("--backend-dir");
    cmd.arg(&backend_dir);
    
    // Check for bundled model weights in resources
    if !cfg!(debug_assertions) {
        // Try multiple possible paths for bundled weights
        let possible_weight_paths = vec![
            "_up_/_up_/models/cavfish_v1/weights.pth",  // Actual bundled path
            "models/cavfish_v1/weights.pth",
            "weights/weights.pth",
        ];
        
        for weight_path in possible_weight_paths {
            if let Some(bundled_model) = app.path_resolver().resolve_resource(weight_path) {
                if bundled_model.exists() {
                    eprintln!("[run_first_time_setup] Found bundled weights at: {:?}", bundled_model);
                    cmd.arg("--bundled-model");
                    cmd.arg(&bundled_model);
                    break;
                }
            }
        }
    }
    
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());
    
    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Failed to start setup: {}", e))?;
    
    // Read output and emit events
    let stdout = child.stdout.take().ok_or("Failed to capture stdout")?;
    let stderr = child.stderr.take().ok_or("Failed to capture stderr")?;
    
    let app_handle = app.clone();
    
    // Spawn thread to read stdout
    let stdout_app = app_handle.clone();
    thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines().flatten() {
            // Parse JSON output from setup script
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
                // Not JSON, emit as log line
                let event = SetupProgressEvent {
                    step: 0,
                    message: line,
                    level: "info".to_string(),
                };
                let _ = stdout_app.emit_all("setup-progress", event);
            }
        }
    });
    
    // Spawn thread to read stderr (just log to console, don't emit events)
    thread::spawn(move || {
        let reader = BufReader::new(stderr);
        for line in reader.lines().flatten() {
            // Only log stderr to console for debugging, don't emit as event
            eprintln!("[setup stderr] {}", line);
        }
    });
    
    // Wait for process to complete
    let status = child.wait().map_err(|e| format!("Setup process error: {}", e))?;
    
    if status.success() {
        Ok(())
    } else {
        Err(format!("Setup failed with exit code: {:?}", status.code()))
    }
}

#[tauri::command]
fn open_setup_logs() -> Result<(), String> {
    let app_data_dir = get_app_data_dir();
    let logs_dir = app_data_dir.join("logs");
    
    // Create logs dir if it doesn't exist
    fs::create_dir_all(&logs_dir).ok();
    
    // Open in Finder/Explorer
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&logs_dir)
            .spawn()
            .map_err(|e| format!("Failed to open logs: {}", e))?;
    }
    
    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg(&logs_dir)
            .spawn()
            .map_err(|e| format!("Failed to open logs: {}", e))?;
    }
    
    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(&logs_dir)
            .spawn()
            .map_err(|e| format!("Failed to open logs: {}", e))?;
    }
    
    Ok(())
}

#[tauri::command]
async fn finish_setup_and_start(state: tauri::State<'_, AppState>) -> Result<String, String> {
    eprintln!("[finish_setup_and_start] Starting backend server...");
    
    // Try to start the backend
    let port = find_free_port().unwrap_or(8008);
    eprintln!("[finish_setup_and_start] Found free port: {}", port);
    
    match spawn_backend(port) {
        Ok((child, url)) => {
            eprintln!("[finish_setup_and_start] Backend started successfully at {}", url);
            *state.backend_process.lock().unwrap() = Some(child);
            *state.backend_url.lock().unwrap() = url.clone();
            *state.setup_complete.lock().unwrap() = true;
            Ok(url)
        }
        Err(e) => {
            eprintln!("[finish_setup_and_start] Backend start failed: {}", e);
            Err(format!("Failed to start backend: {}", e))
        }
    }
}

#[tauri::command]
fn get_app_data_path() -> String {
    get_app_data_dir().to_string_lossy().to_string()
}

// ============================================================================
// Main Application Setup
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
            check_setup_needed,
            check_xcode_tools_installed,
            check_conda_installed,
            check_conda_env_exists,
            run_first_time_setup,
            open_setup_logs,
            finish_setup_and_start,
            get_app_data_path
        ])
        .setup(|app| {
            // Check if setup is needed
            let setup_needed = !is_setup_complete();
            
            if !setup_needed {
                // Setup complete, try to start backend automatically
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
                // Clean up backend process on close
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

