use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri_plugin_shell::process::CommandChild;

/// What the UI needs to talk to the Python engine.
///
/// The engine picks its own free port and mints its own token at startup, then
/// announces both on stdout. Nothing here is hardcoded.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EngineInfo {
    pub port: u16,
    pub token: String,
}

/// Held by Tauri for the life of the app.
#[derive(Default)]
pub struct EngineState {
    pub info: Mutex<Option<EngineInfo>>,
    pub child: Mutex<Option<CommandChild>>,
    /// Set when startup failed, so the UI can show a real reason instead of
    /// spinning forever.
    pub error: Mutex<Option<String>>,
}
