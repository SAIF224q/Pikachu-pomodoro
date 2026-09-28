import { contextBridge, ipcRenderer } from "electron";
contextBridge.exposeInMainWorld("timerApp", {
  loadState: () => ipcRenderer.invoke("state:load"),
  saveState: (state: Record<string, unknown>) => ipcRenderer.invoke("state:save", state),
  close: () => ipcRenderer.invoke("window:close"),
  toggleTopmost: () => ipcRenderer.invoke("window:topmost")
});
