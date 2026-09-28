import { app, BrowserWindow, ipcMain, screen } from "electron";
import fs from "node:fs";
import path from "node:path";

type AppState = { note: string; duration: number; bounds?: Electron.Rectangle; alwaysOnTop: boolean };
const defaultState: AppState = { note: "", duration: 20 * 60, alwaysOnTop: true };
let mainWindow: BrowserWindow | null = null;

function statePath() { return path.join(app.getPath("userData"), "timer-state.json"); }
function loadState(): AppState {
  let saved: Partial<AppState> = {};
  try { saved = JSON.parse(fs.readFileSync(statePath(), "utf8")); } catch { /* First Electron launch. */ }

  if (!saved.note) {
    try {
      const legacy = JSON.parse(fs.readFileSync(path.join(app.getAppPath(), "timer_state.json"), "utf8"));
      if (legacy.note && legacy.note !== "Add a note...") saved.note = legacy.note;
      if (!saved.duration && Number.isFinite(legacy.duration)) saved.duration = legacy.duration;
    } catch { /* No legacy Python state is present. */ }
  }
  return { ...defaultState, ...saved };
}
function saveState(state: AppState) { fs.writeFileSync(statePath(), JSON.stringify(state, null, 2)); }
function validBounds(bounds?: Electron.Rectangle) {
  if (!bounds) return undefined;
  const workArea = screen.getDisplayNearestPoint({ x: bounds.x, y: bounds.y }).workArea;
  return bounds.x > workArea.x - 340 && bounds.y > workArea.y - 220 ? bounds : undefined;
}
function createWindow() {
  const state = loadState();
  mainWindow = new BrowserWindow({
    width: 392, height: 248, minWidth: 392, minHeight: 248, maxWidth: 392, maxHeight: 248,
    ...(validBounds(state.bounds) ? { x: state.bounds!.x, y: state.bounds!.y } : {}),
    frame: false, transparent: true, resizable: false, alwaysOnTop: state.alwaysOnTop,
    backgroundColor: "#00000000",
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, nodeIntegration: false }
  });
  mainWindow.loadFile(path.join(__dirname, "../src/index.html"));
  mainWindow.on("close", () => {
    const current = loadState();
    saveState({ ...current, bounds: mainWindow?.getBounds(), alwaysOnTop: mainWindow?.isAlwaysOnTop() ?? true });
  });
}
app.whenReady().then(() => {
  ipcMain.handle("state:load", () => loadState());
  ipcMain.handle("state:save", (_event, partial: Partial<AppState>) => saveState({ ...loadState(), ...partial }));
  ipcMain.handle("window:close", () => mainWindow?.close());
  ipcMain.handle("window:topmost", () => {
    if (!mainWindow) return true;
    const next = !mainWindow.isAlwaysOnTop(); mainWindow.setAlwaysOnTop(next);
    saveState({ ...loadState(), alwaysOnTop: next }); return next;
  });
  createWindow();
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on("window-all-closed", () => app.quit());
