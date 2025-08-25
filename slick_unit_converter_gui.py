#!/usr/bin/env python3
# slick_unit_converter_gui.py
# Tkinter GUI for slick_unit_converter_plus

import sys, os, json, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List

# Try to import our converter module
MODULE_NAME = "slick_unit_converter_plus"
if MODULE_NAME not in sys.modules:
    # Favor local directory first
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    conv = __import__(MODULE_NAME)
except Exception as e:
    conv = None

APP_TITLE = "Slick Unit Converter — GUI"
APP_WIDTH, APP_HEIGHT = 900, 620

FALLBACK_CATEGORIES = ["angle","area","data","energy","frequency","length","mass","power","pressure","speed","temperature","time","volume"]
FALLBACK_UNITS = {
    "length": ["m","cm","mm","km","in","ft","yd","mi","nmi"],
    "area": ["m2","cm2","mm2","km2","ft2"],
    "volume": ["m3","L","mL","gal","qt","pt","cup"],
    "mass": ["kg","g","mg","lb","oz"],
    "time": ["s","min","h"],
    "speed": ["m/s","kph","km/h","mph"],
    "pressure": ["Pa","kPa","bar","atm","psi"],
    "energy": ["J","kJ","Wh","kWh","cal","kcal"],
    "power": ["W","kW","MW","hp"],
    "frequency": ["Hz","kHz","MHz","GHz"],
    "angle": ["rad","deg"],
    "temperature": ["C","F","K","R"],
    "data": ["B","kB","MB","GB","TB","KiB","MiB","GiB","TiB","bit"],
}

def get_categories() -> List[str]:
    try:
        return conv.list_categories()
    except Exception:
        return FALLBACK_CATEGORIES

def get_units(cat: str) -> List[str]:
    try:
        return conv.list_units(cat)
    except Exception:
        return FALLBACK_UNITS.get(cat, [])

def do_convert_expr(expr: str, as_json=False, table=False) -> str:
    if conv is None:
        return "Error: converter module not found."
    try:
        return conv.do_convert(expr, as_json=as_json, table=table)
    except Exception as e:
        return f"Error: {e}"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.minsize(780, 520)

        # Top title bar
        title = ttk.Label(self, text=APP_TITLE, font=("Segoe UI", 14, "bold"))
        title.pack(pady=(10,4))

        # Notebook tabs
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.simple_tab = ttk.Frame(self.nb)
        self.sentence_tab = ttk.Frame(self.nb)
        self.batch_tab = ttk.Frame(self.nb)
        self.explore_tab = ttk.Frame(self.nb)

        self.nb.add(self.simple_tab, text="Simple Mode")
        self.nb.add(self.sentence_tab, text="Sentence Mode")
        self.nb.add(self.batch_tab, text="Batch Mode")
        self.nb.add(self.explore_tab, text="Explore")

        self._build_simple_tab()
        self._build_sentence_tab()
        self._build_batch_tab()
        self._build_explore_tab()

        # History panel
        self._build_history()

        # Keyboard shortcuts
        self.bind_all("<Control-l>", lambda e: self._clear_all())
        self.bind_all("<Control-s>", lambda e: self._save_batch_results())

    # -------------------- Simple Mode --------------------
    def _build_simple_tab(self):
        frm = self.simple_tab
        top = ttk.Frame(frm)
        top.pack(fill="x", pady=6, padx=6)

        # Value
        ttk.Label(top, text="Value").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.val_entry = ttk.Entry(top, width=12)
        self.val_entry.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self.val_entry.insert(0, "1")

        # From Unit
        ttk.Label(top, text="From Unit").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.from_unit = ttk.Combobox(top, width=18, values=self._all_units())
        self.from_unit.grid(row=0, column=3, sticky="w", padx=4, pady=4)
        self.from_unit.set("m")

        # To Unit
        ttk.Label(top, text="To Unit").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        self.to_unit = ttk.Combobox(top, width=18, values=self._all_units())
        self.to_unit.grid(row=0, column=5, sticky="w", padx=4, pady=4)
        self.to_unit.set("cm")

        # Convert button
        btn = ttk.Button(top, text="Convert", command=self._do_simple_convert)
        btn.grid(row=0, column=6, sticky="w", padx=8)

        # Bind Enter to convert
        self.val_entry.bind("<Return>", lambda e: self._do_simple_convert())
        self.from_unit.bind("<Return>", lambda e: self._do_simple_convert())
        self.to_unit.bind("<Return>", lambda e: self._do_simple_convert())

        # Output
        self.simple_out = tk.Text(frm, height=4, wrap="word")
        self.simple_out.pack(fill="x", padx=6, pady=(8,4))

        tip = ttk.Label(frm, text="Tip: You can type compound units like m/s, kW*h, N*m, kg*m^2/s^2, etc.",
                        foreground="#666")
        tip.pack(anchor="w", padx=8)

    def _all_units(self) -> List[str]:
        units = set()
        for cat in get_categories():
            for u in get_units(cat):
                units.add(u)
        # add common compound shortcuts
        units.update(["m/s","km/h","kph","mph","N*m","kW*h"])
        return sorted(units)

    def _do_simple_convert(self):
        v = self.val_entry.get().strip()
        src = self.from_unit.get().strip()
        dst = self.to_unit.get().strip()
        if not v:
            messagebox.showwarning("Missing value", "Please enter a number.")
            return
        try:
            _ = float(v)
        except ValueError:
            messagebox.showerror("Invalid number", "Value must be numeric (e.g., 12.5).")
            return
        expr = f"{v} {src} to {dst}"
        out = do_convert_expr(expr, as_json=False, table=False)
        self.simple_out.delete("1.0", "end")
        self.simple_out.insert("1.0", out + "\n")
        self._push_history(expr, out)

    # -------------------- Sentence Mode --------------------
    def _build_sentence_tab(self):
        frm = self.sentence_tab
        row = ttk.Frame(frm)
        row.pack(fill="x", padx=6, pady=6)
        ttk.Label(row, text="Expression").pack(side="left")
        self.sentence_entry = ttk.Entry(row)
        self.sentence_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.sentence_entry.insert(0, "convert 3 ft to cm")
        ttk.Button(row, text="Convert", command=self._do_sentence_convert).pack(side="left")
        self.sentence_entry.bind("<Return>", lambda e: self._do_sentence_convert())

        self.sentence_out = tk.Text(frm, height=6, wrap="word")
        self.sentence_out.pack(fill="both", expand=True, padx=6, pady=(4,8))

    def _do_sentence_convert(self):
        expr = self.sentence_entry.get().strip()
        if not expr:
            messagebox.showwarning("Missing input", "Type something like:  5 kg in lb")
            return
        out = do_convert_expr(expr, as_json=False, table=False)
        self.sentence_out.delete("1.0", "end")
        self.sentence_out.insert("1.0", out + "\n")
        self._push_history(expr, out)

    # -------------------- Batch Mode --------------------
    def _build_batch_tab(self):
        frm = self.batch_tab
        top = ttk.Frame(frm)
        top.pack(fill="x", padx=6, pady=6)
        ttk.Button(top, text="Open .txt file…", command=self._open_batch).pack(side="left")
        ttk.Button(top, text="Save results…", command=self._save_batch_results).pack(side="left", padx=6)
        self.table_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Table output", variable=self.table_var).pack(side="left", padx=6)
        self.json_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="JSON output", variable=self.json_var).pack(side="left", padx=6)

        self.batch_in = tk.Text(frm, height=10, wrap="none")
        self.batch_in.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(frm, text="Results").pack(anchor="w", padx=6)
        self.batch_out = tk.Text(frm, height=8, wrap="none")
        self.batch_out.pack(fill="both", expand=True, padx=6, pady=(0,8))

        btns = ttk.Frame(frm); btns.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(btns, text="Run Batch", command=self._run_batch).pack(side="left")

    def _open_batch(self):
        path = filedialog.askopenfilename(title="Open conversions.txt",
                                          filetypes=[("Text files","*.txt"),("All files","*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.batch_in.delete("1.0", "end")
                self.batch_in.insert("1.0", f.read())
        except Exception as e:
            messagebox.showerror("Open error", str(e))

    def _run_batch(self):
        lines = [ln.strip() for ln in self.batch_in.get("1.0","end").splitlines() if ln.strip() and not ln.strip().startswith("#")]
        out_lines = []
        for ln in lines:
            out_lines.append(do_convert_expr(ln, as_json=self.json_var.get(), table=self.table_var.get()))
        self.batch_out.delete("1.0","end")
        self.batch_out.insert("1.0", "\n".join(out_lines))

    def _save_batch_results(self):
        text = self.batch_out.get("1.0","end").strip()
        if not text:
            return
        path = filedialog.asksaveasfilename(title="Save results", defaultextension=".txt",
                                            filetypes=[("Text files","*.txt"),("All files","*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    # -------------------- Explore Tab --------------------
    def _build_explore_tab(self):
        frm = self.explore_tab
        left = ttk.Frame(frm); left.pack(side="left", fill="y", padx=6, pady=6)
        right = ttk.Frame(frm); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        ttk.Label(left, text="Categories").pack(anchor="w")
        self.cat_list = tk.Listbox(left, height=16)
        self.cat_list.pack(fill="y", expand=False)
        for c in get_categories():
            self.cat_list.insert("end", c)
        self.cat_list.bind("<<ListboxSelect>>", self._on_cat_select)

        ttk.Label(right, text="Units").pack(anchor="w")
        self.unit_list = tk.Listbox(right)
        self.unit_list.pack(fill="both", expand=True)

    def _on_cat_select(self, event):
        sel = self.cat_list.curselection()
        if not sel: return
        cat = self.cat_list.get(sel[0])
        self.unit_list.delete(0,"end")
        for u in get_units(cat):
            self.unit_list.insert("end", u)

    # -------------------- History Pane --------------------
    def _build_history(self):
        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=10, pady=(0,10))
        ttk.Label(frame, text="History").pack(anchor="w")
        self.hist = tk.Text(frame, height=4, wrap="none")
        self.hist.pack(fill="x", expand=False)
        btns = ttk.Frame(frame); btns.pack(fill="x")
        ttk.Button(btns, text="Copy Last Result", command=self._copy_last).pack(side="left")
        ttk.Button(btns, text="Clear History (Ctrl+L)", command=self._clear_all).pack(side="left", padx=6)

    def _push_history(self, expr: str, out: str):
        self.hist.insert("end", f"> {expr}\n{out}\n")
        self.hist.see("end")

    def _copy_last(self):
        try:
            lines = self.hist.get("1.0","end").strip().splitlines()
            if not lines: return
            # last non-empty line that's not a prompt
            for line in reversed(lines):
                if line and not line.startswith("> "):
                    self.clipboard_clear()
                    self.clipboard_append(line)
                    self.update()  # keep on clipboard after window closes
                    messagebox.showinfo("Copied", line)
                    return
        except Exception:
            pass

    def _clear_all(self):
        self.hist.delete("1.0","end")
        if hasattr(self, "simple_out"):
            self.simple_out.delete("1.0","end")
        if hasattr(self, "sentence_out"):
            self.sentence_out.delete("1.0","end")

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
