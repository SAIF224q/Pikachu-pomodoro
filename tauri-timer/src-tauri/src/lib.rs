use serde::{Deserialize, Serialize};
use std::{fs, path::PathBuf};
use tauri::{Manager, WebviewWindow};

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(default)]
struct AppState {
    note: String,
    duration: u64,
    always_on_top: bool,
}

impl AppState {
    fn default_state() -> Self {
        Self {
            note: String::new(),
            duration: 20 * 60,
            always_on_top: true,
        }
    }
}

#[derive(Debug, Deserialize)]
struct StateUpdate {
    note: Option<String>,
    duration: Option<u64>,
}

fn state_path<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> Result<PathBuf, String> {
    let dir = app.path().app_data_dir().map_err(|error| error.to_string())?;
    fs::create_dir_all(&dir).map_err(|error| error.to_string())?;
    Ok(dir.join("timer-state.json"))
}

fn read_state<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> Result<AppState, String> {
    let path = state_path(app)?;
    let mut state = AppState::default_state();
    if let Ok(contents) = fs::read_to_string(path) {
        if let Ok(saved) = serde_json::from_str::<AppState>(&contents) {
            state = saved;
        }
    }
    Ok(state)
}

fn write_state<R: tauri::Runtime>(app: &tauri::AppHandle<R>, state: &AppState) -> Result<(), String> {
    let path = state_path(app)?;
    let contents = serde_json::to_string_pretty(state).map_err(|error| error.to_string())?;
    fs::write(path, contents).map_err(|error| error.to_string())
}

#[tauri::command]
fn load_state<R: tauri::Runtime>(app: tauri::AppHandle<R>) -> Result<AppState, String> {
    read_state(&app)
}

#[tauri::command]
fn save_state<R: tauri::Runtime>(app: tauri::AppHandle<R>, update: StateUpdate) -> Result<(), String> {
    let mut state = read_state(&app)?;
    if let Some(note) = update.note {
        state.note = note;
    }
    if let Some(duration) = update.duration {
        state.duration = duration;
    }
    write_state(&app, &state)
}

#[tauri::command]
fn toggle_topmost<R: tauri::Runtime>(app: tauri::AppHandle<R>, window: WebviewWindow<R>) -> Result<bool, String> {
    let next = !window.is_always_on_top().map_err(|error| error.to_string())?;
    window.set_always_on_top(next).map_err(|error| error.to_string())?;
    let mut state = read_state(&app)?;
    state.always_on_top = next;
    write_state(&app, &state)?;
    Ok(next)
}

#[tauri::command]
fn close_window<R: tauri::Runtime>(window: WebviewWindow<R>) -> Result<(), String> {
    window.close().map_err(|error| error.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let window = app.get_webview_window("main").ok_or("main window not found")?;
            let state = read_state(&app.handle())?;
            window.set_always_on_top(state.always_on_top)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![load_state, save_state, toggle_topmost, close_window])
        .run(tauri::generate_context!())
        .expect("error while running Drift Timer");
}
