#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;
use tauri::{Manager};

fn main() {
  tauri::Builder::default()
    .setup(|app| {
      // Choose a stable localhost port for v1
      let port = "8008";

      // In dev: spawn python -m backend.api.cli
      // In prod: spawn packaged sidecar executable.
      #[cfg(debug_assertions)]
      {
        let mut cmd = Command::new("python");
        cmd.args(["-m", "backend.api.cli"]);
        cmd.env("FISH_PORT", port);
        cmd.env("FISH_DEVICE", "cpu");
        cmd.env("FISH_MODEL_DIR", "models/cavfish_v1");
        cmd.spawn().expect("Failed to start backend");
      }

      // Store backend URL for the frontend
      let url = format!("http://127.0.0.1:{}", port);
      app.manage(BackendState { base_url: url });

      Ok(())
    })
    .manage(BackendState { base_url: "http://127.0.0.1:8008".into() })
    .invoke_handler(tauri::generate_handler![get_backend_url])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}

struct BackendState {
  base_url: String,
}

#[tauri::command]
fn get_backend_url(state: tauri::State<BackendState>) -> String {
  state.base_url.clone()
}

