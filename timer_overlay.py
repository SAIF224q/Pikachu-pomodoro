import json
import math
import os
import time
import tkinter as tk
from pathlib import Path
from tkinter import font

try:
    import winsound
except ImportError:  # pragma: no cover - non-Windows fallback
    winsound = None


APP_DIR = Path(__file__).resolve().parent
STATE_PATH = APP_DIR / "timer_state.json"

BG = "#050505"
PANEL = "#185675"
PANEL_DARK = "#0d3549"
CYAN = "#25d8ef"
MUTED = "#a9aaad"
BUTTON = "#303030"
BUTTON_HOVER = "#3b3b3b"
TEXT = "#f7f7f7"


class TimerOverlay(tk.Tk):
    def __init__(self):
        super().__init__()
        self.state = self.load_state()
        self.total_seconds = int(self.state.get("duration", 20 * 60))
        self.remaining = self.total_seconds
        self.running = False
        self.last_tick = None
        self.drag_start = None

        self.title("Hover Timer")
        self.geometry(self.state.get("geometry", "390x206+120+120"))
        self.minsize(330, 178)
        self.configure(bg=BG)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", float(self.state.get("opacity", 0.96)))

        self.title_font = font.Font(family="Segoe UI", size=11, weight="bold")
        self.time_font = font.Font(family="Segoe UI Light", size=44)
        self.note_font = font.Font(family="Segoe UI", size=10)
        self.small_font = font.Font(family="Segoe UI", size=9)

        self.build_ui()
        self.bind_drag(self)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _event: self.close())
        self.bind("<Control-q>", lambda _event: self.close())
        self.after(200, self.tick)

    def load_state(self):
        if not STATE_PATH.exists():
            return {}
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save_state(self):
        self.state.update(
            {
                "duration": self.total_seconds,
                "note": self.note_var.get().strip(),
                "geometry": self.geometry(),
                "opacity": self.attributes("-alpha"),
            }
        )
        STATE_PATH.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def build_ui(self):
        self.shell = tk.Frame(self, bg=BG, bd=0, highlightthickness=0)
        self.shell.pack(fill="both", expand=True, padx=10, pady=10)
        self.shell.grid_columnconfigure(0, weight=1)
        self.shell.grid_columnconfigure(1, minsize=154)
        self.shell.grid_rowconfigure(1, weight=1)

        self.header = tk.Frame(self.shell, bg=BG)
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 0))
        self.header.grid_columnconfigure(0, weight=1)

        tk.Label(
            self.header,
            text="Timer",
            bg=BG,
            fg=MUTED,
            font=self.title_font,
        ).grid(row=0, column=0, sticky="w")

        self.pin_btn = self.small_button(self.header, "Top", self.toggle_topmost, width=4)
        self.pin_btn.grid(row=0, column=1, padx=(0, 6))
        self.close_btn = self.small_button(self.header, "x", self.close, width=2)
        self.close_btn.grid(row=0, column=2)

        self.left = tk.Frame(self.shell, bg=BG)
        self.left.grid(row=1, column=0, sticky="nsew", padx=(10, 6), pady=(4, 0))

        self.time_label = tk.Label(
            self.left,
            text="20:00",
            bg=BG,
            fg=TEXT,
            font=self.time_font,
            anchor="w",
        )
        self.time_label.pack(fill="x", pady=(2, 8))
        self.bind_drag(self.time_label)

        presets = tk.Frame(self.left, bg=BG)
        presets.pack(fill="x", pady=(0, 8))
        for minutes in (5, 10, 20):
            btn = self.preset_button(presets, f"{minutes}m", lambda m=minutes: self.set_duration(m * 60))
            btn.pack(side="left", padx=(0, 6))

        controls = tk.Frame(self.left, bg=BG)
        controls.pack(fill="x")
        self.start_btn = self.control_button(controls, "Start", self.toggle_timer, width=8)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.reset_btn = self.control_button(controls, "Reset", self.reset_timer, width=7)
        self.reset_btn.pack(side="left")

        self.note_var = tk.StringVar(value=self.state.get("note", "Add a note..."))
        self.note_entry = tk.Entry(
            self.left,
            textvariable=self.note_var,
            bg="#151515",
            fg=TEXT,
            insertbackground=CYAN,
            relief="flat",
            font=self.note_font,
            highlightthickness=1,
            highlightbackground="#282828",
            highlightcolor=CYAN,
        )
        self.note_entry.pack(fill="x", pady=(12, 0), ipady=5)
        self.note_entry.bind("<FocusIn>", self.clear_placeholder)
        self.note_entry.bind("<FocusOut>", self.restore_placeholder)
        self.note_entry.bind("<KeyRelease>", lambda _event: self.save_state())

        self.canvas = tk.Canvas(
            self.shell,
            width=148,
            height=148,
            bg=BG,
            bd=0,
            highlightthickness=0,
        )
        self.canvas.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=(2, 0))
        self.bind_drag(self.canvas)
        self.canvas.bind("<Button-1>", lambda _event: self.toggle_timer())
        self.canvas.bind("<Configure>", lambda _event: self.draw_ring())

        self.opacity = tk.Scale(
            self.shell,
            from_=70,
            to=100,
            orient="horizontal",
            showvalue=False,
            bg=BG,
            fg=TEXT,
            troughcolor="#161616",
            activebackground=CYAN,
            highlightthickness=0,
            bd=0,
            length=88,
            command=self.set_opacity,
        )
        self.opacity.set(int(float(self.attributes("-alpha")) * 100))
        self.opacity.grid(row=2, column=1, sticky="e", padx=(0, 20), pady=(0, 2))

        self.draw_ring()

    def bind_drag(self, widget):
        widget.bind("<ButtonPress-3>", self.start_drag)
        widget.bind("<B3-Motion>", self.on_drag)
        widget.bind("<ButtonRelease-3>", self.end_drag)
        widget.bind("<ButtonPress-2>", self.start_drag)
        widget.bind("<B2-Motion>", self.on_drag)
        widget.bind("<ButtonRelease-2>", self.end_drag)

    def small_button(self, parent, text, command, width):
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg="#202020",
            fg=MUTED,
            activebackground=BUTTON_HOVER,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            font=self.small_font,
            cursor="hand2",
        )

    def preset_button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=5,
            bg=PANEL if text == "20m" else "#393939",
            fg=CYAN if text == "20m" else TEXT,
            activebackground=PANEL_DARK,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            font=self.small_font,
            cursor="hand2",
        )

    def control_button(self, parent, text, command, width):
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=BUTTON,
            fg=TEXT,
            activebackground=BUTTON_HOVER,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            font=self.title_font,
            cursor="hand2",
        )

    def start_drag(self, event):
        self.drag_start = (event.x_root, event.y_root, self.winfo_x(), self.winfo_y())

    def on_drag(self, event):
        if not self.drag_start:
            return
        start_x, start_y, win_x, win_y = self.drag_start
        self.geometry(f"+{win_x + event.x_root - start_x}+{win_y + event.y_root - start_y}")

    def end_drag(self, _event):
        self.drag_start = None
        self.save_state()

    def clear_placeholder(self, _event):
        if self.note_var.get() == "Add a note...":
            self.note_var.set("")

    def restore_placeholder(self, _event):
        if not self.note_var.get().strip():
            self.note_var.set("Add a note...")
        self.save_state()

    def set_duration(self, seconds):
        self.total_seconds = int(seconds)
        self.remaining = self.total_seconds
        self.running = False
        self.last_tick = None
        self.start_btn.configure(text="Start")
        self.update_display()
        self.save_state()

    def toggle_timer(self):
        self.running = not self.running
        self.last_tick = time.monotonic()
        self.start_btn.configure(text="Pause" if self.running else "Start")
        self.draw_ring()

    def reset_timer(self):
        self.running = False
        self.remaining = self.total_seconds
        self.last_tick = None
        self.start_btn.configure(text="Start")
        self.update_display()

    def toggle_topmost(self):
        current = bool(self.attributes("-topmost"))
        self.attributes("-topmost", not current)
        self.pin_btn.configure(text="Top" if not current else "Free")

    def set_opacity(self, value):
        self.attributes("-alpha", int(value) / 100)
        self.save_state()

    def tick(self):
        if self.running:
            now = time.monotonic()
            elapsed = now - (self.last_tick or now)
            self.last_tick = now
            self.remaining = max(0, self.remaining - elapsed)
            if self.remaining <= 0:
                self.running = False
                self.start_btn.configure(text="Start")
                self.notify_finished()
            self.update_display()
        self.after(200, self.tick)

    def notify_finished(self):
        self.lift()
        if winsound:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

    def update_display(self):
        minutes = int(self.remaining) // 60
        seconds = int(self.remaining) % 60
        self.time_label.configure(text=f"{minutes:02d}:{seconds:02d}")
        self.draw_ring()

    def draw_ring(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        size = min(width if width > 20 else 148, height if height > 20 else 148)
        pad = 12
        cx = cy = size / 2
        radius = (size / 2) - pad

        self.canvas.create_oval(2, 2, size - 2, size - 2, fill=PANEL, outline="")
        self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            outline="#0d4057",
            width=13,
        )

        progress = 0 if self.total_seconds <= 0 else self.remaining / self.total_seconds
        extent = max(0.0, min(1.0, progress)) * 359.9
        self.canvas.create_arc(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            start=90,
            extent=-extent,
            style="arc",
            outline=CYAN,
            width=13,
        )

        inner = radius - 23
        self.canvas.create_oval(cx - inner, cy - inner, cx + inner, cy + inner, fill=BG, outline="")
        icon = "II" if self.running else "▶"
        icon_size = 27 if self.running else 25
        self.canvas.create_text(cx, cy - 1, text=icon, fill=TEXT, font=("Segoe UI", icon_size, "bold"))

        if self.remaining <= 0:
            for i in range(10):
                angle = math.radians(i * 36)
                x = cx + math.cos(angle) * (radius + 2)
                y = cy - math.sin(angle) * (radius + 2)
                self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=CYAN, outline="")

    def close(self):
        self.save_state()
        self.destroy()


if __name__ == "__main__":
    os.chdir(APP_DIR)
    app = TimerOverlay()
    app.update_display()
    app.mainloop()
