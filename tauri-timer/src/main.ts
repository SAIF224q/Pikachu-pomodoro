import "./style.css";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";

type SavedState = { note: string; duration: number; always_on_top: boolean };
const time = document.querySelector<HTMLOutputElement>("#time")!;
const start = document.querySelector<HTMLButtonElement>("#start")!;
const reset = document.querySelector<HTMLButtonElement>("#reset")!;
const orb = document.querySelector<HTMLButtonElement>("#orb")!;
const note = document.querySelector<HTMLInputElement>("#note")!;
const progress = document.querySelector<SVGCircleElement>("#progress")!;
const pikachu = document.querySelector<HTMLImageElement>("#pikachu")!;
const pin = document.querySelector<HTMLButtonElement>("#pin")!;
const presets = [...document.querySelectorAll<HTMLButtonElement>("[data-minutes]")];
const ringLength = 2 * Math.PI * 65;
let total = 20 * 60, remaining = total, running = false, lastTick = 0, timerId: number | undefined;

function render() {
  const minutes = Math.floor(remaining / 60).toString().padStart(2, "0");
  const seconds = Math.ceil(remaining % 60).toString().padStart(2, "0");
  time.value = `${minutes}:${seconds}`;
  progress.style.strokeDashoffset = String(ringLength * (1 - Math.max(0, Math.min(1, remaining / total))));
  start.innerHTML = running ? '<span class="pause-mark">&#9612;&#9612;</span><span>Pause</span>' : '<span class="play-mark">&#9654;</span><span>Start</span>';
  pikachu.src = running ? "/Pikachu run.gif" : "/Pikachu stop.gif";
  document.body.classList.toggle("is-running", running);
}

function stopClock() { running = false; if (timerId !== undefined) window.clearInterval(timerId); timerId = undefined; render(); }
function tick() { const now = performance.now(); remaining = Math.max(0, remaining - (now - lastTick) / 1000); lastTick = now; if (remaining <= 0) { stopClock(); document.body.classList.add("finished"); window.setTimeout(() => document.body.classList.remove("finished"), 1500); } else render(); }
function toggle() { if (remaining <= 0) remaining = total; if (running) stopClock(); else { running = true; lastTick = performance.now(); timerId = window.setInterval(tick, 120); render(); } }
function setDuration(seconds: number) { stopClock(); total = seconds; remaining = seconds; presets.forEach((button) => button.classList.toggle("selected", Number(button.dataset.minutes) * 60 === seconds)); void invoke("save_state", { update: { duration: seconds } }); render(); }

async function initialize() {
  const state = await invoke<SavedState>("load_state");
  total = state.duration || total;
  remaining = total;
  note.value = state.note || "";
  presets.forEach((button) => button.classList.toggle("selected", Number(button.dataset.minutes) * 60 === total));
  pin.classList.toggle("active", state.always_on_top);
  render();
}

start.addEventListener("click", toggle);
orb.addEventListener("click", toggle);
reset.addEventListener("click", () => { stopClock(); remaining = total; render(); });
presets.forEach((button) => button.addEventListener("click", () => setDuration(Number(button.dataset.minutes) * 60)));
note.addEventListener("input", () => void invoke("save_state", { update: { note: note.value.trim() } }));
pin.addEventListener("click", async () => pin.classList.toggle("active", await invoke<boolean>("toggle_topmost")));
document.querySelector<HTMLButtonElement>("#close")!.addEventListener("click", () => void invoke("close_window"));
document.querySelector<HTMLElement>("#drag-bar")!.addEventListener("mousedown", (event) => {
  if ((event.target as HTMLElement).closest("button")) return;
  void getCurrentWindow().startDragging();
});
void initialize();
