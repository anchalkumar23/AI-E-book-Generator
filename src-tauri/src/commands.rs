use crate::state::{EngineInfo, EngineState};
use serde::Serialize;
use tauri::{AppHandle, Manager};

/// Three states matter to the UI: still starting, ready, or failed. Without the
/// distinction the UI cannot tell "wait a moment" from "this is broken" — which
/// is how you get an infinite splash screen.
#[derive(Serialize, Clone)]
pub struct EngineStatus {
    /// "starting" | "ready" | "failed"
    pub state: String,
    pub info: Option<EngineInfo>,
    pub message: Option<String>,
}

/// The UI polls this on boot.
#[tauri::command]
pub fn engine_status(app: AppHandle) -> EngineStatus {
    let state = app.state::<EngineState>();

    if let Some(info) = state.info.lock().unwrap().clone() {
        return EngineStatus {
            state: "ready".into(),
            info: Some(info),
            message: None,
        };
    }
    if let Some(message) = state.error.lock().unwrap().clone() {
        return EngineStatus {
            state: "failed".into(),
            info: None,
            message: Some(message),
        };
    }
    EngineStatus {
        state: "starting".into(),
        info: None,
        message: None,
    }
}

/// Kills any existing engine and starts a fresh one.
///
/// Takes AppHandle rather than State because the mutex guards must be dropped
/// before the `.await` below — a std Mutex guard cannot be held across an await.
#[tauri::command]
pub async fn restart_engine(app: AppHandle) -> Result<EngineInfo, String> {
    {
        let state = app.state::<EngineState>();
        let old = state.child.lock().unwrap().take();
        if let Some(child) = old {
            let _ = child.kill();
        }
        *state.info.lock().unwrap() = None;
        *state.error.lock().unwrap() = None;
    } // guards dropped here, before the await

    match crate::engine::start(&app).await {
        Ok((info, child)) => {
            let state = app.state::<EngineState>();
            *state.info.lock().unwrap() = Some(info.clone());
            *state.child.lock().unwrap() = Some(child);
            Ok(info)
        }
        Err(e) => {
            let state = app.state::<EngineState>();
            *state.error.lock().unwrap() = Some(e.clone());
            Err(e)
        }
    }
}
