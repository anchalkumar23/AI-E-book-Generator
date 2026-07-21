use crate::state::EngineInfo;
use serde::Deserialize;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;
use tokio::time::{timeout, Duration};

/// The one line the engine prints on stdout once uvicorn is listening.
#[derive(Deserialize)]
struct Handshake {
    ready: bool,
    port: u16,
    token: String,
}

/// Starts the Python engine and waits for its handshake line.
///
/// Dev builds run Python straight from backend/venv so Python edits need only an
/// app restart — no rebuild, no freezing. Release builds run the PyInstaller
/// sidecar binary bundled into the installer.
pub async fn start(app: &AppHandle) -> Result<(EngineInfo, CommandChild), String> {
    // Store the database in the OS app-data dir, not next to the executable.
    let db_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&db_dir).map_err(|e| e.to_string())?;
    let db_arg = db_dir.to_string_lossy().to_string();

    let (mut rx, child) = if cfg!(debug_assertions) {
        app.shell()
            .command("../backend/venv/Scripts/python.exe")
            .args(["-m", "app.engine", &db_arg])
            .current_dir(
                std::env::current_dir()
                    .map_err(|e| e.to_string())?
                    .join("../backend"),
            )
            .spawn()
            .map_err(|e| format!("failed to start dev engine: {e}"))?
    } else {
        app.shell()
            .sidecar("pageforge-engine")
            .map_err(|e| format!("sidecar not found: {e}"))?
            .args([&db_arg])
            .spawn()
            .map_err(|e| format!("failed to start engine: {e}"))?
    };

    // Collect stderr so a crash reports the real Python traceback rather than a
    // generic "engine failed".
    let mut stderr = String::new();
    let wait = async {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes);
                    if let Ok(h) = serde_json::from_str::<Handshake>(line.trim()) {
                        if h.ready {
                            return Ok(EngineInfo {
                                port: h.port,
                                token: h.token,
                            });
                        }
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    stderr.push_str(&String::from_utf8_lossy(&bytes));
                }
                CommandEvent::Terminated(_) => {
                    return Err(format!("engine exited before handshake:\n{stderr}"));
                }
                _ => {}
            }
        }
        Err(format!("engine stream closed before handshake:\n{stderr}"))
    };

    // 30s was too tight: importing FastAPI + the providers takes ~3s on an idle
    // machine but far longer under memory pressure, so the app failed to launch
    // on exactly the low-RAM machines that need the most patience. This only
    // bounds a hang — a healthy start still completes in seconds.
    const STARTUP_SECS: u64 = 120;
    match timeout(Duration::from_secs(STARTUP_SECS), wait).await {
        Ok(result) => result.map(|info| (info, child)),
        Err(_) => Err(format!(
            "The engine did not start within {STARTUP_SECS} seconds. \
             The machine may be low on memory — close other apps and try again."
        )),
    }
}
