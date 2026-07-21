mod commands;
mod engine;
mod state;

use state::EngineState;
use tauri::{Manager, RunEvent};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(EngineState::default())
        .invoke_handler(tauri::generate_handler![
            commands::engine_status,
            commands::restart_engine
        ])
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Start the Python engine in the background so the window opens
            // immediately; the UI shows a "Starting engine…" gate until the
            // handshake lands.
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let state = handle.state::<EngineState>();
                match engine::start(&handle).await {
                    Ok((info, child)) => {
                        *state.info.lock().unwrap() = Some(info);
                        *state.child.lock().unwrap() = Some(child);
                    }
                    Err(e) => {
                        // Stored so the UI can show the real reason.
                        eprintln!("ENGINE FAILED: {e}");
                        *state.error.lock().unwrap() = Some(e);
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|handle, event| {
            // Kill the Python child so it never outlives the window.
            if let RunEvent::Exit = event {
                let state = handle.state::<EngineState>();
                // Bind the guard's result before `state` drops: inlining this
                // keeps the MutexGuard temporary alive past `state`'s lifetime.
                let child = state.child.lock().unwrap().take();
                if let Some(child) = child {
                    let _ = child.kill();
                }
            }
        });
}
