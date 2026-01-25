#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::env;
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;

// ============================================================================
// State & Types
// ============================================================================

#[derive(Clone)]
struct BackendState {
    base_url: String,
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

/// Spawn backend process
fn spawn_backend(port: u16) -> Result<String, String> {
    let backend_exe = if cfg!(debug_assertions) {
        // In dev, use python directly
        "python3".to_string()
    } else {
        // In prod, use sidecar binary
        let exe_name = if cfg!(windows) {
            "fish_backend.exe"
        } else {
            "fish_backend"
        };

        // Find sidecar relative to app bundle
        let sidecar_path = if cfg!(target_os = "macos") {
            PathBuf::from(format!("../Resources/{}", exe_name))
        } else if cfg!(windows) {
            PathBuf::from(format!("../{}", exe_name))
        } else {
            PathBuf::from(format!("../lib/{}", exe_name))
        };

        sidecar_path.to_string_lossy().to_string()
    };

    let mut cmd = Command::new(&backend_exe);

    if cfg!(debug_assertions) {
        cmd.args(["-m", "backend.api.cli"]);
    }

    cmd.env("FISH_PORT", port.to_string());
    cmd.env("FISH_DEVICE", env::var("FISH_DEVICE").unwrap_or_else(|_| "cpu".to_string()));
    cmd.env(
        "FISH_MODEL_DIR",
        env::var("FISH_MODEL_DIR").unwrap_or_else(|_| "models/cavfish_v1".to_string()),
    );

    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());

    let _child = cmd
        .spawn()
        .map_err(|e| format!("Failed to spawn backend: {}", e))?;

    // Wait for server to be ready (simple polling)
    let base_url = format!("http://127.0.0.1:{}", port);
    let start = std::time::Instant::now();
    let timeout = Duration::from_secs(30);

    loop {
        if start.elapsed() > timeout {
            return Err("Backend startup timeout (30s)".to_string());
        }

        // Simple TCP check instead of HTTP
        if TcpListener::bind(format!("127.0.0.1:{}", port)).is_err() {
            // Port is in use, server is likely running
            return Ok(base_url);
        }

        thread::sleep(Duration::from_millis(500));
    }
}

// ============================================================================
// Tauri Commands
// ============================================================================

#[tauri::command]
fn get_backend_url(state: tauri::State<BackendState>) -> String {
    state.base_url.clone()
}

// ============================================================================
// Main Application Setup
// ============================================================================

fn main() {
    // In development: connect to already-running backend on port 8008
    // In production: spawn backend as sidecar
    let backend_url = if cfg!(debug_assertions) {
        // Development: assume backend is already running on 8008
        "http://127.0.0.1:8008".to_string()
    } else {
        // Production: spawn sidecar backend on random free port
        let port = find_free_port().unwrap_or(8008);
        spawn_backend(port)
            .unwrap_or_else(|e| {
                eprintln!("Warning: Failed to start backend: {}", e);
                format!("http://127.0.0.1:{}", port)
            })
    };

    tauri::Builder::default()
        .manage(BackendState {
            base_url: backend_url.clone(),
        })
        .invoke_handler(tauri::generate_handler![get_backend_url])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

