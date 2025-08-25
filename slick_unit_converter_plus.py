#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slick Unit Converter Plus
- CLI + GUI (Tkinter) in one file
- Advanced unit parsing: "convert 3 ft to cm", "5 kg in lb", "100 kph to mph", "32 F to C"
- Categories covered: angle, area, data, energy, frequency, length, mass, power,
  pressure, speed, temperature, time, volume
- GUI niceties:
    * Clean ttk UI with category/unit pickers + search
    * Keypad (0-9, ., ±, C, ⌫) and Math buttons (+ − × ÷ ^ ( ) √ sin cos tan π e =)
    * Deg/Rad toggle for trig eval
    * History with copy; Swap units; Clipboard integration
    * Batch tab to paste multiple lines and convert all
    * Optional Drag & Drop for text/files if tkinterdnd2 is installed (fallback safe)
- Safe math evaluator (AST) for keypad expression before conversion
- Windows-friendly; no external deps required (tkinterdnd2 is optional)

Usage:
    python slick_unit_converter_plus.py --list
    python slick_unit_converter_plus.py "convert 3 ft to cm"
    python slick_unit_converter_plus.py --repl
    python slick_unit_converter_plus.py --gui

If no args are given, GUI launches by default.
"""
from __future__ import annotations
import argparse
import math
import re
import sys
import json
from dataclasses import dataclass
from typing import Callable, Dict, Tuple, Optional, List

# -------- Conversion Engine --------

@dataclass(frozen=True)
class Unit:
    name: str
    to_base: Callable[[float], float]
    from_base: Callable[[float], float]
    aliases: Tuple[str, ...] = ()

class UnitRegistry:
    def __init__(self):
        self.categories: Dict[str, Dict[str, Unit]] = {}

    def add(self, category: str, name: str, factor: float=None, offset: float=0.0,
            to_base: Callable[[float], float]=None,
            from_base: Callable[[float], float]=None,
            aliases: Tuple[str, ...] = ()):
        cat = self.categories.setdefault(category, {})
        if to_base is None and from_base is None:
            # linear unit: base * factor + offset
            def _to_base(x: float, f=factor, b=offset): return (x + 0.0 - 0.0*b) * f if b == 0 else (x + (-b)) * f
            def _from_base(x: float, f=factor, b=offset): return (x / f) + b
            u = Unit(name, _to_base, _from_base, tuple({name, *aliases}))
        else:
            u = Unit(name, to_base, from_base, tuple({name, *aliases}))
        for alias in {name, *aliases}:
            cat[alias.lower()] = u

    def get(self, category: str, unit_key: str) -> Optional[Unit]:
        return self.categories.get(category, {}).get(unit_key.lower())

    def detect_category(self, a: str, b: str) -> Optional[str]:
        al = a.lower(); bl = b.lower()
        for cat, units in self.categories.items():
            if al in units and bl in units:
                return cat
        return None

    def list_categories(self) -> List[str]:
        return sorted(self.categories.keys())

    def list_units(self, category: str) -> List[str]:
        seen = {}
        for u in self.categories.get(category, {}).values():
            seen[u.name] = True
        return sorted(seen.keys())

ureg = UnitRegistry()

# Helper to add linear units: base unit factor = 1
def add_linear(category, base_name, pairs):
    # base unit
    ureg.add(category, base_name, factor=1.0, aliases=(base_name,))
    for name, factor, aliases in pairs:
        ureg.add(category, name, factor=factor, aliases=aliases)

# Length (base: meter)
add_linear('length', 'm', [
    ('km', 1000.0, ('kilometer','kilometre','kilometers','kilometres','kms')),
    ('cm', 0.01, ('centimeter','centimetre','centimeters','centimetres','cms')),
    ('mm', 0.001, ('millimeter','millimetre','millimeters','millimetres','mms')),
    ('μm', 1e-6, ('um','micrometer','micrometre','micron','microns')),
    ('nm', 1e-9, ('nanometer','nanometre','nanometers','nanometres')),
    ('in', 0.0254, ('inch','inches','"')),
    ('ft', 0.3048, ('foot','feet','\'')),
    ('yd', 0.9144, ('yard','yards')),
    ('mi', 1609.344, ('mile','miles')),
])

# Mass (base: kilogram)
add_linear('mass', 'kg', [
    ('g', 0.001, ('gram','grams')),
    ('mg', 1e-6, ('milligram','milligrams')),
    ('lb', 0.45359237, ('lbs','pound','pounds')),
    ('oz', 0.028349523125, ('ounce','ounces')),
    ('ton', 1000.0, ('t','tonne','tonnes','metric ton','metric tons')),
])

# Time (base: second)
add_linear('time', 's', [
    ('ms', 1e-3, ('millisecond','milliseconds')),
    ('μs', 1e-6, ('us','microsecond','microseconds')),
    ('min', 60.0, ('minute','minutes')),
    ('h', 3600.0, ('hr','hour','hours')),
    ('day', 86400.0, ('days','d')),
])

# Speed (base: m/s)
ureg.add('speed', 'm/s', factor=1.0, aliases=('mps','meter/second','metre/second','meters/second','metres/second'))
ureg.add('speed', 'km/h', factor=1000.0/3600.0, aliases=('kph','kmph','kilometer/hour','kilometre/hour'))
ureg.add('speed', 'mph', factor=1609.344/3600.0, aliases=('mile/hour','miles/hour'))
ureg.add('speed', 'ft/s', factor=0.3048, aliases=('fps','foot/second','feet/second','ftps'))
ureg.add('speed', 'kn', factor=1852.0/3600.0, aliases=('knot','knots'))

# Pressure (base: pascal)
add_linear('pressure', 'Pa', [
    ('kPa', 1000.0, ()),
    ('bar', 1e5, ()),
    ('mbar', 100.0, ('millibar','hPa')),
    ('atm', 101325.0, ()),
    ('psi', 6894.757293168, ('pound-force/in^2','lb/in^2')),
])

# Energy (base: joule)
add_linear('energy', 'J', [
    ('kJ', 1000.0, ()),
    ('Wh', 3600.0, ('watt-hour','watt hour')),
    ('kWh', 3.6e6, ('kilowatt-hour','kilowatt hour')),
    ('cal', 4.184, ('small calorie','calorie')),
    ('kcal', 4184.0, ('Cal','food calorie')),
    ('eV', 1.602176634e-19, ()),
])

# Power (base: watt)
add_linear('power', 'W', [
    ('kW', 1000.0, ()),
    ('MW', 1e6, ()),
    ('hp', 745.6998715822702, ('horsepower',)),
])

# Frequency (base: hertz)
add_linear('frequency', 'Hz', [
    ('kHz', 1e3, ()),
    ('MHz', 1e6, ()),
    ('GHz', 1e9, ()),
    ('rpm', 1/60.0, ()),
])

# Area (base: m^2)
add_linear('area', 'm^2', [
    ('cm^2', 1e-4, ()),
    ('mm^2', 1e-6, ()),
    ('km^2', 1e6, ()),
    ('in^2', 0.00064516, ()),
    ('ft^2', 0.09290304, ()),
    ('yd^2', 0.83612736, ()),
    ('acre', 4046.8564224, ()),
    ('hectare', 10000.0, ('ha',)),
])

# Volume (base: m^3)
add_linear('volume', 'm^3', [
    ('L', 0.001, ('liter','litre','liters','litres')),
    ('mL', 1e-6, ('ml','milliliter','millilitre')),
    ('cm^3', 1e-6, ('cc','cubic centimeter','cubic centimetre')),
    ('in^3', 1.6387064e-5, ('cu in',)),
    ('ft^3', 0.028316846592, ('cu ft',)),
    ('gal', 0.003785411784, ('gallon','gallons','US gal')),
    ('qt', 0.000946352946, ('quart','quarts')),
    ('pt', 0.000473176473, ('pint','pints')),
    ('fl oz', 2.95735295625e-5, ('fluid ounce','fl. oz.')),
])

# Data (base: byte)
add_linear('data', 'B', [
    ('KB', 1024.0, ()), ('MB', 1024.0**2, ()), ('GB', 1024.0**3, ()),
    ('TB', 1024.0**4, ()), ('bit', 1/8.0, ('b',)), ('Kb', 1024.0/8.0, ()),
    ('Mb', (1024.0**2)/8.0, ()), ('Gb', (1024.0**3)/8.0, ()), ('Tb', (1024.0**4)/8.0, ()),
])

# Angle (base: radian)
ureg.add('angle', 'rad', factor=1.0, aliases=('radian','radians'))
ureg.add('angle', 'deg', factor=math.pi/180.0, aliases=('degree','degrees'))
ureg.add('angle', 'grad', factor=math.pi/200.0, aliases=('gon','grade'))
ureg.add('angle', 'turn', factor=2*math.pi, aliases=('rev','revolution'))

# Temperature (non-linear; base: Kelvin)
def C_to_K(x): return x + 273.15
def K_to_C(x): return x - 273.15
def F_to_K(x): return (x - 32.0) * 5.0/9.0 + 273.15
def K_to_F(x): return (x - 273.15) * 9.0/5.0 + 32.0
def R_to_K(x): return x * 5.0/9.0
def K_to_R(x): return x * 9.0/5.0
ureg.add('temperature', 'K', to_base=lambda x: x, from_base=lambda x: x, aliases=('kelvin','kelvins','k'))
ureg.add('temperature', 'C', to_base=C_to_K, from_base=K_to_C, aliases=('°C','celsius','degC'))
ureg.add('temperature', 'F', to_base=F_to_K, from_base=K_to_F, aliases=('°F','fahrenheit','degF'))
ureg.add('temperature', 'R', to_base=R_to_K, from_base=K_to_R, aliases=('rankine','°R'))

# Parser
EXPR_PAT = re.compile(
    r'^\s*(?:convert\s+)?(?P<value>[-+*/^().\w\s]+?)\s*(?P<from>[^\d\s][^0-9]*?)\s+(?:to|in)\s+(?P<to>.+?)\s*$',
    re.IGNORECASE
)

def safe_eval(expr: str, mode_deg: bool=False) -> float:
    """
    Safely evaluate arithmetic expressions with +,-,*,/,^,(,), sqrt, sin, cos, tan, pi, e.
    Trig uses radians by default; deg=True interprets inputs in degrees.
    """
    import ast
    expr = expr.replace('^', '**')
    allowed_names = {
        'pi': math.pi, 'e': math.e,
        'sqrt': math.sqrt,
        'sin': (lambda x: math.sin(math.radians(x))) if mode_deg else math.sin,
        'cos': (lambda x: math.cos(math.radians(x))) if mode_deg else math.cos,
        'tan': (lambda x: math.tan(math.radians(x))) if mode_deg else math.tan,
        'abs': abs, 'round': round
    }
    allowed_nodes = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Num,
                     ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
                     ast.USub, ast.UAdd, ast.Mod, ast.FloorDiv, ast.Name, ast.Constant,
                     ast.Tuple, ast.List)
    node = ast.parse(expr, mode='eval')
    for n in ast.walk(node):
        if not isinstance(n, allowed_nodes):
            raise ValueError(f"Disallowed expression element: {type(n).__name__}")
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name) or n.func.id not in allowed_names:
                raise ValueError("Only sqrt/sin/cos/tan/abs/round, pi, e are allowed.")
    return eval(compile(node, '<expr>', 'eval'), {'__builtins__': {}}, allowed_names)

def parse_and_convert(s: str, deg_mode=False) -> Tuple[float, str, str, float, str]:
    """
    Returns: (value, from_unit, category, out_value, to_unit)
    """
    m = EXPR_PAT.match(s)
    if not m:
        raise ValueError("Could not parse expression. Try like: 3 ft to cm  |  5 kg in lb")
    val_expr = m.group('value').strip()
    u_from = m.group('from').strip()
    u_to = m.group('to').strip()
    # Evaluate value expression safely
    try:
        value = float(safe_eval(val_expr, mode_deg=deg_mode))
    except Exception:
        # If plain float fails, try direct float()
        value = float(val_expr)
    # Detect category
    cat = ureg.detect_category(u_from, u_to)
    if not cat:
        # try plural forms trim or power suffix normalize
        # For some units like "kph" vs "km/h" already in aliases, so fallback fails => error
        raise ValueError(f"Cannot detect a common category for '{u_from}' and '{u_to}'.")
    uf = ureg.get(cat, u_from)
    ut = ureg.get(cat, u_to)
    if not uf or not ut:
        raise ValueError("Unknown unit(s). Use --list to see categories/units.")
    x_base = uf.to_base(value)
    y = ut.from_base(x_base)
    return value, uf.name, cat, y, ut.name

# -------- CLI / REPL --------

def cmd_list(category: Optional[str]=None):
    if category:
        units = ureg.list_units(category)
        if not units:
            print(f"No such category: {category}")
        else:
            for u in units:
                print(u)
    else:
        for c in ureg.list_categories():
            print(c)

def cmd_repl():
    print("Advanced Unit Converter REPL")
    print("Commands:")
    print("  <expr> like:  3 ft to cm   |  5 kg in lb  | convert 100 kph to mph")
    print("  :list                  — list categories")
    print("  :list <category>       — list units")
    print("  :deg / :rad            — toggle trig eval mode for math in value")
    print("  :quit / :q / :exit     — exit")
    deg = False
    while True:
        try:
            s = input("» ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not s:
            continue
        if s in (':quit', ':q', ':exit'):
            break
        if s == ':deg':
            deg = True; print("Trig mode: degrees")
            continue
        if s == ':rad':
            deg = False; print("Trig mode: radians")
            continue
        if s.startswith(':list'):
            parts = s.split()
            if len(parts) == 1:
                cmd_list()
            else:
                cmd_list(parts[1])
            continue
        try:
            v, uf, cat, y, ut = parse_and_convert(s, deg_mode=deg)
            print(f"{v:g} {uf} = {y:g} {ut}   [{cat}]")
        except Exception as e:
            print(f"Error: {e}")

# -------- GUI --------

def launch_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    # Optional drag-n-drop
    try:
        import tkinterdnd2 as tkdnd
        DND_AVAILABLE = True
    except Exception:
        tkdnd = None
        DND_AVAILABLE = False

    root = tk.Tk()
    root.title("Slick Unit Converter Plus")
    root.geometry("900x560")
    root.minsize(800, 520)
    root.option_add('*tearOff', False)

    style = ttk.Style(root)
    try:
        style.theme_use('vista' if sys.platform.startswith('win') else 'clam')
    except Exception:
        pass

    deg_mode = tk.BooleanVar(value=False)

    def categories():
        return ureg.list_categories()

    # Top: Input row
    top = ttk.Frame(root, padding=12)
    top.pack(side=tk.TOP, fill=tk.X)

    ttk.Label(top, text="Value").grid(row=0, column=0, sticky='w', padx=(0,6))
    val_var = tk.StringVar(value="")
    val_entry = ttk.Entry(top, textvariable=val_var, width=20, font=('Segoe UI', 12))
    val_entry.grid(row=1, column=0, sticky='we', padx=(0,12))

    ttk.Label(top, text="Category").grid(row=0, column=1, sticky='w', padx=(0,6))
    cat_var = tk.StringVar(value='length')
    cat_cb = ttk.Combobox(top, textvariable=cat_var, values=categories(), state='readonly', width=18)
    cat_cb.grid(row=1, column=1, sticky='we', padx=(0,12))

    ttk.Label(top, text="From").grid(row=0, column=2, sticky='w', padx=(0,6))
    from_var = tk.StringVar()
    from_cb = ttk.Combobox(top, textvariable=from_var, width=18)
    from_cb.grid(row=1, column=2, sticky='we', padx=(0,12))

    ttk.Label(top, text="To").grid(row=0, column=3, sticky='w', padx=(0,6))
    to_var = tk.StringVar()
    to_cb = ttk.Combobox(top, textvariable=to_var, width=18)
    to_cb.grid(row=1, column=3, sticky='we', padx=(0,12))

    swap_btn = ttk.Button(top, text="Swap ⟷")
    swap_btn.grid(row=1, column=4, sticky='we')

    # Result
    mid = ttk.Frame(root, padding=(12,0,12,0))
    mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    left = ttk.Frame(mid)
    left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    res_var = tk.StringVar(value="")
    res_entry = ttk.Entry(left, textvariable=res_var, font=('Segoe UI', 14, 'bold'))
    res_entry.pack(side=tk.TOP, fill=tk.X, pady=(6,6))

    # Buttons row
    btn_row = ttk.Frame(left)
    btn_row.pack(side=tk.TOP, fill=tk.X)
    convert_btn = ttk.Button(btn_row, text="Convert (Enter)")
    convert_btn.pack(side=tk.LEFT, padx=(0,6))
    copy_btn = ttk.Button(btn_row, text="Copy Result")
    copy_btn.pack(side=tk.LEFT, padx=(0,6))
    ttk.Checkbutton(btn_row, text="Trig in degrees", variable=deg_mode).pack(side=tk.LEFT)

    # History
    hist_frame = ttk.LabelFrame(left, text="History")
    hist_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(8,0))
    hist_list = tk.Listbox(hist_frame, height=8)
    hist_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    hist_scroll = ttk.Scrollbar(hist_frame, command=hist_list.yview)
    hist_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    hist_list.config(yscrollcommand=hist_scroll.set)

    # Right: Keypad + Math
    right = ttk.Frame(mid)
    right.pack(side=tk.LEFT, fill=tk.Y, padx=(12,0))

    pad = ttk.LabelFrame(right, text="Keypad & Math")
    pad.pack(side=tk.TOP, fill=tk.X)

    def insert(text):
        val_entry.insert(tk.INSERT, text)
        val_entry.focus_set()

    def backspace():
        s = val_var.get()
        if s:
            val_var.set(s[:-1])

    def clear_val():
        val_var.set("")

    # Keypad layout
    keys = [
        ['7','8','9','/','⌫'],
        ['4','5','6','*','('],
        ['1','2','3','-',')'],
        ['0','.','±','+','C'],
    ]
    for r, row in enumerate(keys):
        f = ttk.Frame(pad)
        f.pack(fill=tk.X)
        for k in row:
            def mkcmd(x=k):
                if x == '⌫':
                    return backspace
                if x == 'C':
                    return clear_val
                if x == '±':
                    def toggle_sign():
                        s = val_var.get().strip()
                        if s.startswith('-'):
                            val_var.set(s[1:])
                        else:
                            val_var.set('-' + s if s else '-')
                    return toggle_sign
                def _cmd():
                    insert(x)
                return _cmd
            b = ttk.Button(f, text=k, command=mkcmd(), width=4)
            b.pack(side=tk.LEFT, padx=2, pady=2)

    # Math buttons
    mathf = ttk.Frame(pad)
    mathf.pack(fill=tk.X, pady=(6,0))
    for label, token in [('^','^'),('√','sqrt('),('sin','sin('),('cos','cos('),('tan','tan('),('π','pi'),('e','e'),('=','=')]:
        def mkcmd(tok=token):
            def _():
                if tok == '=':
                    # Try to evaluate just the expression in value field
                    try:
                        val = safe_eval(val_var.get() or '0', mode_deg=deg_mode.get())
                        val_var.set(str(val))
                    except Exception as e:
                        messagebox.showerror("Eval error", str(e))
                else:
                    insert(tok)
            return _
        ttk.Button(mathf, text=label, command=mkcmd()).pack(side=tk.LEFT, padx=2, pady=2)

    # Batch tab below history
    bottom = ttk.Frame(root, padding=12)
    bottom.pack(side=tk.TOP, fill=tk.BOTH)
    nb = ttk.Notebook(bottom)
    nb.pack(fill=tk.BOTH, expand=True)

    batch_tab = ttk.Frame(nb)
    nb.add(batch_tab, text="Batch")

    ttk.Label(batch_tab, text="Enter one conversion per line (e.g., '3 ft to cm')").pack(anchor='w')
    batch_txt = tk.Text(batch_tab, height=6)
    batch_txt.pack(fill=tk.BOTH, expand=True, pady=6)
    batch_res = tk.Text(batch_tab, height=6, state='disabled')
    batch_res.pack(fill=tk.BOTH, expand=True)

    batch_btns = ttk.Frame(batch_tab)
    batch_btns.pack(fill=tk.X, pady=6)
    def run_batch():
        lines = batch_txt.get('1.0', 'end').strip().splitlines()
        out_lines = []
        for line in lines:
            if not line.strip():
                continue
            try:
                v, uf, cat, y, ut = parse_and_convert(line, deg_mode=deg_mode.get())
                out_lines.append(f"{v:g} {uf} = {y:g} {ut}   [{cat}]")
            except Exception as e:
                out_lines.append(f"[error] {line}  →  {e}")
        batch_res.config(state='normal')
        batch_res.delete('1.0','end')
        batch_res.insert('1.0', '\n'.join(out_lines))
        batch_res.config(state='disabled')
    ttk.Button(batch_btns, text="Run Batch", command=run_batch).pack(side=tk.LEFT)
    def open_file():
        path = filedialog.askopenfilename(title="Open text file", filetypes=[('Text','*.txt'),('All','*.*')])
        if not path:
            return
        try:
            with open(path,'r',encoding='utf-8',errors='ignore') as f:
                batch_txt.delete('1.0','end')
                batch_txt.insert('1.0', f.read())
        except Exception as e:
            messagebox.showerror("Open failed", str(e))
    ttk.Button(batch_btns, text="Open .txt…", command=open_file).pack(side=tk.LEFT, padx=6)

    # Populate units when category changes
    def refresh_units(*_):
        units = ureg.list_units(cat_var.get())
        from_cb['values'] = units
        to_cb['values'] = units
        if units:
            if not from_var.get(): from_var.set(units[0])
            if not to_var.get(): to_var.set(units[1] if len(units)>1 else units[0])
    cat_cb.bind('<<ComboboxSelected>>', refresh_units)
    refresh_units()

    def do_swap():
        a, b = from_var.get(), to_var.get()
        from_var.set(b); to_var.set(a)
    swap_btn.config(command=do_swap)

    def do_convert(evt=None):
        s = f"{val_var.get()} {from_var.get()} to {to_var.get()}"
        try:
            v, uf, cat, y, ut = parse_and_convert(s, deg_mode=deg_mode.get())
            res_var.set(f"{v:g} {uf} = {y:g} {ut}   [{cat}]")
            hist_list.insert(tk.END, res_var.get())
            hist_list.see(tk.END)
        except Exception as e:
            messagebox.showerror("Conversion error", str(e))
    convert_btn.config(command=do_convert)
    root.bind('<Return>', do_convert)

    def do_copy():
        root.clipboard_clear()
        root.clipboard_append(res_var.get())
    copy_btn.config(command=do_copy)

    # History double-click to copy
    def copy_sel(_evt):
        try:
            sel = hist_list.get(hist_list.curselection())
            root.clipboard_clear(); root.clipboard_append(sel)
        except Exception:
            pass
    hist_list.bind('<Double-Button-1>', copy_sel)

    # Drag & Drop (optional)
    if DND_AVAILABLE:
        app = tkdnd.TkinterDnD.Tk()  # Not used as root already created; bind to widgets via tkdnd
        def handle_drop(event):
            data = event.data
            # If it's a file path, load to batch
            if data and data.startswith('{') and data.endswith('}'):
                # Could be multiple files; we take first
                path = data.strip('{}').split('} {')[0]
                try:
                    with open(path,'r',encoding='utf-8',errors='ignore') as f:
                        batch_txt.delete('1.0','end'); batch_txt.insert('1.0', f.read())
                    nb.select(batch_tab)
                except Exception as e:
                    messagebox.showerror("Drop failed", str(e))
            else:
                # Treat as text dropped into value
                val_entry.delete(0,'end'); val_entry.insert(0, data)
        try:
            # Enable drops on window and entry/text
            for widget in (root, val_entry, batch_txt):
                widget.drop_target_register('*')
                widget.dnd_bind('<<Drop>>', handle_drop)
        except Exception:
            pass
    else:
        # Provide a subtle hint label
        hint = ttk.Label(bottom, text="Tip: Install 'tkinterdnd2' to enable drag-and-drop of text or .txt files.", foreground='#666')
        hint.pack(anchor='w', pady=(6,0))

    # Status bar
    status = ttk.Label(root, anchor='w', padding=(12,4), text="Ready. Type a value or use the keypad. Press Enter to convert.")
    status.pack(side=tk.BOTTOM, fill=tk.X)

    # Accessibility: focus value
    val_entry.focus_set()
    root.mainloop()

# -------- Main --------

def main(argv=None):
    p = argparse.ArgumentParser(description="Slick Unit Converter Plus")
    p.add_argument('expr', nargs='?', help='Expression like: "3 ft to cm" or "5 kg in lb"')
    p.add_argument('--list', nargs='?', const=True, help='List categories or units for a category')
    p.add_argument('--repl', action='store_true', help='Run interactive REPL')
    p.add_argument('--gui', action='store_true', help='Launch GUI')
    p.add_argument('--deg', action='store_true', help='Interpret math in value using degrees for trig')
    args = p.parse_args(argv)

    if args.list is not None and args.list is not True:
        cmd_list(args.list)
        return 0
    if args.list is True:
        cmd_list()
        return 0
    if args.repl:
        cmd_repl()
        return 0
    if args.gui or (args.expr is None and not args.repl and args.list is None):
        # Launch GUI by default when no args
        launch_gui()
        return 0
    if args.expr:
        try:
            v, uf, cat, y, ut = parse_and_convert(args.expr, deg_mode=args.deg)
            print(f"{v:g} {uf} = {y:g} {ut}   [{cat}]")
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    p.print_help()
    return 0

if __name__ == '__main__':
    sys.exit(main())
