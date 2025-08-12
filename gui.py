#!/usr/bin/env python3
# GUI to set Komplete Kontrol key-up / key-down LED colors via HID
# - Adds a model selector matching your CLI menu
# - Uses MK2 0xA4 report with buffer[5] = key-up, buffer[6] = key-down
# - On MK1 selection, shows a warning (different protocol)

import tkinter as tk
from tkinter import ttk, messagebox
import hid

VENDOR_ID = 0x17cc  # Native Instruments

MODELS = [
    # (label, mode, product_id, nb_keys, offset)
    ("Komplete Kontrol S61 MK2", "MK2", 0x1620, 61, -36),  # 1
    ("Komplete Kontrol S88 MK2", "MK2", 0x1630, 88, -21),  # 2
    ("Komplete Kontrol S49 MK2", "MK2", 0x1610, 49, -36),  # 3
    # ("Komplete Kontrol S61 MK1", "MK1", 0x1360, 61, -36),  # 4
    # ("Komplete Kontrol S88 MK1", "MK1", 0x1410, 88, -21),  # 5
    # ("Komplete Kontrol S49 MK1", "MK1", 0x1350, 49, -36),  # 6
    # ("Komplete Kontrol S25 MK1", "MK1", 0x1340, 25, -21),  # 7
]

# Intensity offsets within each color family
INTENSITY = {
    "Low": 0,
    "Medium": 1,
    "High": 2,
    "Saturated": 3,
}

# Base codes per your map (each + 0..3 for intensity)
COLOR_BASE = {
    "OFF":      0x00,
    "RED":      0x04,
    "ORANGE":   0x08,
    "L ORANGE": 0x0C,
    "W YELLOW": 0x10,
    "YELLOW":   0x14,
    "L GREEN":  0x18,
    "GREEN":    0x1C,
    "MINT":     0x20,
    "TURQUOISE":0x24,
    "CYAN":     0x28,
    "BLUE":     0x2C,
    "PLUM":     0x30,
    "VIOLET":   0x34,
    "PURPLE":   0x38,
    "MAGENTA":  0x3C,
    "FUCHSIA":  0x40,
    "WHITE":    0x44,
}

# Your working 0xA4 buffer template (MK2): index 5 = up color, 6 = down color
BUFFER_TEMPLATE_A4 = [
    0xA4,0x7F,0x00,0x00,0x33,0x00,0x00,0x00,0x00,0x7F,0x00,
    0x00,0x33,0x2C,0x2E,0x00,0x00,0x7F,0x00,0x00,0x33,0x2C,
    0x2E,0x00,0x00,0x7F,0x00,0x00,0x33,0x2C,0x2E,0x00,0x00,
    0x7F,0x00,0x00,0x33,0x2C,0x2E,0x00,0x00,0x7F,0x00,0x00,
    0x33,0x2C,0x2E,0x00,0x00,0x7F,0x00,0x00,0x33,0x2C,0x2E,
    0x00,0x00,0x7F,0x00,0x00,0x33,0x2C,0x2E,0x00,0x00,0x7F,
    0x00,0x00,0x33,0x2C,0x2E,0x00,0x00,0x7F,0x00,0x00,0x33,
    0x2C,0x2E,0x00,0x00,0x7F,0x00,0x00,0x33,0x2C,0x2E,0x00,
    0x00,0x7F,0x00,0x00,0x33,0x2C,0x2E,0x00,0x00,0x7F,0x00,
    0x00,0x33,0x2C,0x2E,0x00,0x00,0x7F,0x00,0x00,0x33,0x2C,
    0x2E,0x00,0x00,0x7F,0x00,0x00,0x33,0x2C,0x2E,0x00,0x00,
    0x7F,0x00,0x00,0x33,0x2C,0x2E,0x00,0x00
]

def compute_code(color_name: str, intensity_name: str) -> int:
    if color_name == "OFF":
        return COLOR_BASE[color_name]

    return COLOR_BASE[color_name] + INTENSITY[intensity_name]


class KKController:
    def __init__(self):
        self.dev = None
        self.mode = None  # "MK1" or "MK2"
        self.product_id = None
        self.nb_keys = None
        self.offset = None

    def select_model(self, label: str):
        for (lbl, mode, pid, keys, off) in MODELS:
            if lbl == label:
                self.mode = mode
                self.product_id = pid
                self.nb_keys = keys
                self.offset = off
                return
        raise ValueError("Unknown model selected")

    def connect(self):
        if self.dev:
            return
        if self.product_id is None:
            raise RuntimeError("No model selected")
        self.dev = hid.device()
        self.dev.open(VENDOR_ID, self.product_id)

        
        if self.mode == "MK2":
            # init lights as off, red when pressed
            buf = list(BUFFER_TEMPLATE_A4)
            buf[5] = 0x03
            buf[6] = 0x06

            self.dev.write(buf)
        else:
            self.dev.write([0xA0, 0x00, 0x00])

    def close(self):
        if self.dev:
            try:
                self.dev.close()
            finally:
                self.dev = None

    def apply_key_up_down(self, up_code: int, down_code: int):
        if not self.dev:
            raise RuntimeError("Device not connected")
        if self.mode != "MK2":
            raise RuntimeError("Key Up/Down color scheme via 0xA4 is only supported on MK2 in this tool.")

        buf = list(BUFFER_TEMPLATE_A4)
        buf[5] = up_code
        buf[6] = down_code
        self.dev.write(buf)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Komplete Kontrol – Key Up/Down Colors")
        self.resizable(False, False)

        self.device = KKController()

        pad = {'padx': 8, 'pady': 6}

        # Model selector
        ttk.Label(self, text="Keyboard Model").grid(row=0, column=0, sticky="e", **pad)
        self.model_combo = ttk.Combobox(self, values=[m[0] for m in MODELS], state="readonly", width=28)
        self.model_combo.set(MODELS[0][0])  # default to S61 MK2
        self.model_combo.grid(row=0, column=1, columnspan=3, sticky="w", **pad)

        # Up selectors
        ttk.Label(self, text="Key Up Color").grid(row=1, column=0, sticky="e", **pad)
        self.up_color = ttk.Combobox(self, values=list(COLOR_BASE.keys()), state="readonly", width=14)
        self.up_color.set("BLUE")
        self.up_color.grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(self, text="Intensity").grid(row=1, column=2, sticky="e", **pad)
        self.up_intensity = ttk.Combobox(self, values=list(INTENSITY.keys()), state="readonly", width=12)
        self.up_intensity.set("Low")
        self.up_intensity.grid(row=1, column=3, sticky="w", **pad)

        # Down selectors
        ttk.Label(self, text="Key Down Color").grid(row=2, column=0, sticky="e", **pad)
        self.down_color = ttk.Combobox(self, values=list(COLOR_BASE.keys()), state="readonly", width=14)
        self.down_color.set("BLUE")
        self.down_color.grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(self, text="Intensity").grid(row=2, column=2, sticky="e", **pad)
        self.down_intensity = ttk.Combobox(self, values=list(INTENSITY.keys()), state="readonly", width=12)
        self.down_intensity.set("High")
        self.down_intensity.grid(row=2, column=3, sticky="w", **pad)

        # Buttons
        self.btn_connect = ttk.Button(self, text="Connect", command=self.on_connect)
        self.btn_apply   = ttk.Button(self, text="Apply",   command=self.on_apply, state="disabled")
        self.btn_quit    = ttk.Button(self, text="Quit",     command=self.on_quit)

        self.btn_connect.grid(row=3, column=0, **pad)
        self.btn_apply.grid(row=3, column=1, **pad)
        self.btn_quit.grid(row=3, column=3, **pad)

        # Status
        self.status = ttk.Label(self, text="Not connected.", foreground="gray")
        self.status.grid(row=4, column=0, columnspan=4, sticky="w", **pad)

        self.protocol("WM_DELETE_WINDOW", self.on_quit)

    def on_connect(self):
        try:
            self.device.select_model(self.model_combo.get())
            self.device.connect()
            self.status.config(
                text=f"Connected to {self.model_combo.get()} (mode {self.device.mode}, PID 0x{self.device.product_id:04X})."
            )
            self.btn_apply.config(state="normal")
            if self.device.mode == "MK1":
                messagebox.showinfo(
                    "MK1 Notice",
                    "MK1 uses a different LED protocol (0x82 with RGB triplets per key).\n"
                    "This tool’s Key Up/Down scheme (0xA4) is MK2-specific.\n"
                    "Apply will show an error on MK1."
                )
        except Exception as e:
            messagebox.showerror("Connect failed", str(e))

    def on_apply(self):
        try:
            up_code = compute_code(self.up_color.get(), self.up_intensity.get())
            down_code = compute_code(self.down_color.get(), self.down_intensity.get())
            self.device.apply_key_up_down(up_code, down_code)
            self.status.config(
                text=f"Applied: Up={self.up_color.get()} {self.up_intensity.get()} (0x{up_code:02X}), "
                     f"Down={self.down_color.get()} {self.down_intensity.get()} (0x{down_code:02X})"
            )
        except Exception as e:
            messagebox.showerror("Apply failed", str(e))

    def on_quit(self):
        try:
            self.device.close()
        finally:
            self.destroy()

if __name__ == "__main__":
    App().mainloop()
