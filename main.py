#!/usr/bin/env python3
"""
Compact Budget Tracker
Author: John Marc Gonzales (c) 2025

Version 1.1.0

Features:
 - USD & PHP currency support (simple adjustable rate)
 - Light/Dark soft red themed UI (toggle)
 - Modernized responsive layout (cards, paned window, dynamic resizing)
 - Track income & expenses with categories
 - Edit existing transactions
 - Custom date range & live search / category / type filters
 - Import CSV (date,type,category,description,amount,currency)
 - Monthly category budgets; shows Remaining & Over/Under
 - Visualizations (Matplotlib):
     * Spending over current month (line)
     * Expenses by category (pie)
     * Income vs expenses (bar)
 - Quick Add pop-up
 - Transaction Templates (save/apply)
 - Export to CSV / Excel (.xlsx) without heavy deps (openpyxl optional)
 - Data Entry Reminders (daily + weekly) via app pop-ups
 - Single-file implementation for simplicity
 - Data persisted to JSON (transactions, budgets, settings, templates)

Notes:
 - Kept code compact; some compromises on separation of concerns.
 - For larger apps, split into modules & add proper MVC structure.
"""
import os
import json
import csv
import datetime as dt
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from math import fsum
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# -------- Optional Dependencies (Charts / Excel) --------
# Matplotlib is optional; if missing, charts tab will show a notice instead of crashing.
try:  # pragma: no cover
    from matplotlib.figure import Figure  # type: ignore
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # type: ignore
except Exception:  # ImportError or backend issues
    Figure = None  # Fallback flag

# openpyxl is optional (Excel export). We import guardedly so editors won't error out;
# if missing, Excel option is hidden. Install with: pip install openpyxl
try:  # pragma: no cover
    from openpyxl import Workbook  # type: ignore
    HAS_OPENPYXL = True
except Exception:  # ImportError
    HAS_OPENPYXL = False
    Workbook = None  # type: ignore

DATA_FILE = 'data.json'
VERSION = '1.1.0'
# Global data container (loaded at runtime); initialized to satisfy linters
data: Dict = {}

# ---------------- Data Models -----------------
@dataclass
class Transaction:
    id: int
    date: str  # ISO date
    ttype: str  # 'income' or 'expense'
    category: str
    description: str
    amount_base: float  # stored in base currency (USD)
    currency: str  # original entry currency (USD or PHP)
    amount_orig: float

@dataclass
class Template:
    name: str
    ttype: str
    category: str
    description: str
    amount: float
    currency: str

# --------------- Persistence Layer ---------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            'transactions': [],
            'next_id': 1,
            'budgets': {},  # category -> monthly budget (base)
            'settings': {
                'base_currency': 'USD',  # internal base
                'display_currency': 'USD',
                'php_rate': 58.0,  # 1 USD = X PHP (editable)
                'theme': 'light',
                'daily_reminder_time': '21:00',
                'weekly_reminder_day': 'Sun',
                'weekly_reminder_time': '21:00'
            },
            'templates': [],
        }
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# --------------- Utility -----------------
WEEKDAYS = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
SOFT_RED_LIGHT = {
    'bg': '#f8f5f5',
    'panel': '#f0d9d9',
    'accent': '#b33b3b',
    'accent_fg': '#ffffff',
    'text': '#3a2a2a',
    'danger': '#d9534f'
}
SOFT_RED_DARK = {
    'bg': '#2b1f1f',
    'panel': '#4a2f2f',
    'accent': '#d05858',
    'accent_fg': '#ffffff',
    'text': '#f3eaea',
    'danger': '#ff6b6b'
}

def convert_to_base(amount: float, currency: str) -> float:
    rate = data['settings']['php_rate']
    if currency == 'USD':
        return amount
    elif currency == 'PHP':
        return amount / rate
    return amount

def convert_from_base(amount_base: float) -> float:
    disp = data['settings']['display_currency']
    rate = data['settings']['php_rate']
    return amount_base if disp == 'USD' else amount_base * rate

def currency_symbol() -> str:
    return '$' if data['settings']['display_currency'] == 'USD' else '₱'

# --------------- Core Logic -----------------

def current_month_filter(tr: Dict) -> bool:
    """Return True if transaction dict is in current month."""
    d = dt.date.fromisoformat(tr['date'])
    today = dt.date.today()
    return d.year == today.year and d.month == today.month

def list_transactions() -> List[Transaction]:
    return data['transactions']

def add_transaction(ttype, category, description, amount, currency):
    tid = data['next_id']; data['next_id'] += 1
    tr = Transaction(
        id=tid,
        date=dt.date.today().isoformat(),
        ttype=ttype,
        category=category,
        description=description,
        amount_base=round(convert_to_base(amount, currency), 2),
        currency=currency,
        amount_orig=amount
    )
    data['transactions'].append(asdict(tr))
    save_data()


def monthly_totals():
    trans = [t for t in data['transactions'] if current_month_filter(t)]
    expenses = [t['amount_base'] for t in trans if t['ttype']=='expense']
    income = [t['amount_base'] for t in trans if t['ttype']=='income']
    return fsum(income), fsum(expenses)

def category_spend():
    trans = [t for t in data['transactions'] if current_month_filter(t)]
    cat_map = {}
    for t in trans:
        if t['ttype']=='expense':
            cat_map.setdefault(t['category'],0.0)
            cat_map[t['category']]+= t['amount_base']
    return cat_map

def remaining_budget(category: Optional[str]=None):
    cat_map = category_spend()
    budgets = data['budgets']
    if category:
        b = budgets.get(category,0.0)
        used = cat_map.get(category,0.0)
        return b - used
    total_budget = fsum(budgets.values())
    total_used = fsum(cat_map.values())
    return total_budget - total_used

# --------------- UI -----------------
class BudgetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # Window basics
        self.title('Budget Tracker - John Marc Gonzales')
        self.geometry('1250x760')
        self.minsize(1100,700)
        # Style object
        self.style = ttk.Style(self)
        # Build UI and initialize
        self._build_ui()
        self.apply_theme()
        self.refresh_all()
        self.schedule_reminder_check()

    # ---- Theme ----
    def apply_theme(self):
        theme = SOFT_RED_DARK if data['settings']['theme']=='dark' else SOFT_RED_LIGHT
        self.configure(bg=theme['bg'])
        for frame in [self.top_bar, self.left_panel, self.main_panel, self.stats_bar]:
            frame.configure(bg=theme['panel'])
        # Style
        self.style.configure('TButton', padding=5)
        for btn in self.winfo_children():
            pass
        # Update text colors
        for label in self.dynamic_labels:
            label.configure(bg=theme['panel'], fg=theme['text'])
        self.remaining_lbl.configure(fg=theme['accent'])
        self.update_idletasks()

    # ---- Build UI ----
    def _build_ui(self):
        self.dynamic_labels = []
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        # Top bar
        self.top_bar = tk.Frame(self, height=46)
        self.top_bar.grid(row=0, column=0, sticky='ew')
        self.top_bar.grid_columnconfigure(50, weight=1)
        # Filter bar
        self.filter_bar = tk.Frame(self, height=40)
        self.filter_bar.grid(row=1, column=0, sticky='ew')
        self.filter_bar.grid_columnconfigure(30, weight=1)
        # Paned central area
        self.paned = tk.PanedWindow(self, orient='horizontal', sashrelief='raised', sashwidth=6, opaqueresize=False)
        self.paned.grid(row=2, column=0, sticky='nsew')
        self.left_panel = tk.Frame(self.paned)
        self.main_panel = tk.Frame(self.paned)
        self.paned.add(self.left_panel, stretch='always', minsize=500)
        self.paned.add(self.main_panel, stretch='always')
        # Status / stats bar
        self.stats_bar = tk.Frame(self, height=32)
        self.stats_bar.grid(row=3, column=0, sticky='ew')

        # Top bar controls (grouped for clarity)
        def tb_btn(txt, cmd):
            return tk.Button(self.top_bar, text=txt, command=cmd, cursor='hand2')
        tb_btn('Add', self.open_add).grid(row=0, column=0, padx=3, pady=4)
        tb_btn('Quick', lambda: self.open_add(quick=True)).grid(row=0, column=1, padx=3)
        tb_btn('Edit', self.edit_selected).grid(row=0, column=2, padx=3)
        tb_btn('Delete', self.delete_selected).grid(row=0, column=3, padx=3)
        tb_btn('Templates', self.open_templates).grid(row=0, column=4, padx=3)
        tb_btn('Budgets', self.open_budgets).grid(row=0, column=5, padx=3)
        tb_btn('Charts', self.open_charts).grid(row=0, column=6, padx=3)
        tb_btn('Import', self.import_csv).grid(row=0, column=7, padx=3)
        tb_btn('Export', self.export_data).grid(row=0, column=8, padx=3)
        tb_btn('Settings', self.open_settings).grid(row=0, column=9, padx=3)
        tb_btn('Theme', self.toggle_theme).grid(row=0, column=10, padx=3)
        tk.Label(self.top_bar, text='Currency:').grid(row=0, column=11, padx=(15,2))
        self.currency_var = tk.StringVar(value=data['settings']['display_currency'])
        tk.OptionMenu(self.top_bar, self.currency_var, 'USD','PHP', command=self.change_currency).grid(row=0, column=12, padx=2)
        tk.Label(self.top_bar, text='v'+VERSION).grid(row=0, column=13, padx=12)

        # Filter bar inputs
        self.start_date_var = tk.StringVar(); self.end_date_var = tk.StringVar(); self.search_var = tk.StringVar();
        self.filter_type_var = tk.StringVar(value='All')
        self.filter_category_var = tk.StringVar(value='All')
        def fb_label(txt, col): tk.Label(self.filter_bar, text=txt).grid(row=0, column=col, padx=2)
        fb_label('Start',0); tk.Entry(self.filter_bar, textvariable=self.start_date_var, width=10).grid(row=0, column=1)
        fb_label('End',2); tk.Entry(self.filter_bar, textvariable=self.end_date_var, width=10).grid(row=0, column=3)
        fb_label('Type',4); ttk.Combobox(self.filter_bar, textvariable=self.filter_type_var, values=['All','income','expense'], width=8, state='readonly').grid(row=0, column=5)
        fb_label('Category',6); self.category_combo = ttk.Combobox(self.filter_bar, textvariable=self.filter_category_var, values=['All'], width=14, state='readonly'); self.category_combo.grid(row=0, column=7)
        fb_label('Search',8); tk.Entry(self.filter_bar, textvariable=self.search_var, width=18).grid(row=0, column=9, sticky='ew')
        tk.Button(self.filter_bar, text='Apply', command=self.refresh_transactions).grid(row=0, column=10, padx=4)
        tk.Button(self.filter_bar, text='Clear', command=self.clear_filters).grid(row=0, column=11, padx=2)
        self.search_var.trace_add('write', lambda *_: self.refresh_transactions())

        # Left panel: Transactions list with scrollbars
        list_container = tk.Frame(self.left_panel)
        list_container.pack(fill='both', expand=True, padx=4, pady=(4,2))
        cols = ('id','date','type','cat','desc','amt')
        self.tr_tree = ttk.Treeview(list_container, columns=cols, show='headings')
        headings = {'id':'ID','date':'Date','type':'Type','cat':'Category','desc':'Description','amt':'Amount'}
        widths = {'id':40,'date':90,'type':70,'cat':120,'desc':260,'amt':110}
        for c in cols:
            self.tr_tree.heading(c, text=headings[c])
            self.tr_tree.column(c, width=widths[c], anchor='w', stretch=(c!='id'))
        vsb = ttk.Scrollbar(list_container, orient='vertical', command=self.tr_tree.yview)
        hsb = ttk.Scrollbar(list_container, orient='horizontal', command=self.tr_tree.xview)
        self.tr_tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tr_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)
        # Main panel: Overview cards
        self.main_panel.grid_rowconfigure(3, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.overview_frame = tk.Frame(self.main_panel)
        self.overview_frame.grid(row=0, column=0, sticky='ew', padx=6, pady=6)
        # Cards
        self.cards_frame = tk.Frame(self.main_panel)
        self.cards_frame.grid(row=1, column=0, sticky='ew', padx=6)
        self.cards_frame.grid_columnconfigure((0,1,2), weight=1)
        self.income_lbl = self._card(self.cards_frame, 'Income')
        self.expense_lbl = self._card(self.cards_frame, 'Expenses', col=1)
        self.remaining_lbl = self._card(self.cards_frame, 'Remaining Budget', col=2, big=True)
        # Budget summary expansive
        self.budget_summary = tk.Label(self.main_panel, font=('Arial', 11), anchor='w', wraplength=560, justify='left')
        self.budget_summary.grid(row=2, column=0, sticky='ew', padx=10, pady=(4,2))
        tk.Label(self.main_panel, text='(c) John Marc Gonzales', font=('Arial',9,'italic')).grid(row=4, column=0, pady=4, sticky='e')

    def _dyn_label(self, parent):
        lbl = tk.Label(parent, font=('Arial', 12))
        lbl.pack(pady=4)
        self.dynamic_labels.append(lbl)
        return lbl

    def _card(self, parent, title, col=0, big=False):
        frame = tk.Frame(parent, bd=0, highlightthickness=0, padx=12, pady=10)
        frame.grid(row=0, column=col, sticky='nsew', padx=5, pady=4)
        parent.grid_columnconfigure(col, weight=1)
        title_lbl = tk.Label(frame, text=title, font=('Arial',10,'bold'))
        title_lbl.pack(anchor='w')
        val_lbl = tk.Label(frame, font=('Arial', 20 if big else 16,'bold'))
        val_lbl.pack(anchor='w')
        self.dynamic_labels.append(title_lbl)
        self.dynamic_labels.append(val_lbl)
        return val_lbl

    # ---- Data Refresh ----
    def refresh_all(self):
        self.refresh_transactions()
        self.refresh_overview()

    def refresh_transactions(self):
        for i in self.tr_tree.get_children():
            self.tr_tree.delete(i)
        sym = currency_symbol()
        filtered = self.apply_filters(list_transactions())
        # update category combo values
        cats = sorted(set(t['category'] for t in list_transactions()))
        self.category_combo.configure(values=['All']+cats)
        for t in reversed(filtered[-800:]):  # show last 800 filtered
            disp_amt = convert_from_base(t['amount_base'])
            self.tr_tree.insert('', 'end', values=(t['id'], t['date'], t['ttype'], t['category'], t['description'], f"{sym}{disp_amt:,.2f}"))

    def refresh_overview(self):
        inc, exp = monthly_totals()
        sym = currency_symbol()
        self.income_lbl.config(text=f"Monthly Income: {sym}{convert_from_base(inc):,.2f}")
        self.expense_lbl.config(text=f"Monthly Expenses: {sym}{convert_from_base(exp):,.2f}")
        rem = remaining_budget(); self.remaining_lbl.config(text=f"{sym}{convert_from_base(rem):,.2f}")
        # Category status text
        parts = []
        for cat, bud in data['budgets'].items():
            used = category_spend().get(cat,0.0)
            status = 'OK'
            if used > bud: status = 'OVER'
            parts.append(f"{cat}: {sym}{convert_from_base(bud-used):,.2f} left ({status})")
        self.budget_summary.config(text=' | '.join(parts) if parts else 'No category budgets set.')

    # ---- Event Handlers ----
    def open_add(self, quick=False, template: Optional[Template]=None):
        win = tk.Toplevel(self); win.title('Add Transaction')
        win.geometry('320x340')
        entries = {}
        def add_field(label, default=''):
            tk.Label(win, text=label).pack()
            var = tk.StringVar(value=default)
            ent = tk.Entry(win, textvariable=var); ent.pack(fill='x', padx=6)
            entries[label]=var
        add_field('Description', template.description if template else '')
        add_field('Category', template.category if template else '')
        add_field('Amount', str(template.amount) if template else '')
        tk.Label(win, text='Type').pack(); ttype_var = tk.StringVar(value=template.ttype if template else 'expense')
        ttk.Combobox(win, textvariable=ttype_var, values=['expense','income']).pack(fill='x', padx=6)
        tk.Label(win, text='Currency').pack(); cur_var = tk.StringVar(value=template.currency if template else data['settings']['display_currency'])
        ttk.Combobox(win, textvariable=cur_var, values=['USD','PHP']).pack(fill='x', padx=6)
        if not quick:
            save_tpl_var = tk.BooleanVar()
            tk.Checkbutton(win, text='Save as Template', variable=save_tpl_var).pack(pady=4)
        def submit():
            try:
                amt = float(entries['Amount'].get())
            except: return messagebox.showerror('Error','Invalid amount')
            add_transaction(ttype_var.get(), entries['Category'].get(), entries['Description'].get(), amt, cur_var.get())
            if not quick and 'save_tpl_var' in locals() and save_tpl_var.get():
                data['templates'].append(asdict(Template(
                    name=entries['Description'].get()[:20] or 'Template',
                    ttype=ttype_var.get(),
                    category=entries['Category'].get(),
                    description=entries['Description'].get(),
                    amount=amt,
                    currency=cur_var.get()
                )))
                save_data()
            self.refresh_all()
            win.destroy()
        tk.Button(win, text='Add', command=submit).pack(pady=10)

    def open_templates(self):
        win = tk.Toplevel(self); win.title('Templates'); win.geometry('360x300')
        tree = ttk.Treeview(win, columns=('name','type','cat','amt'), show='headings')
        for c in ('name','type','cat','amt'): tree.heading(c, text=c.title())
        tree.pack(fill='both', expand=True)
        for tpl in data['templates']:
            tree.insert('', 'end', values=(tpl['name'], tpl['ttype'], tpl['category'], f"{tpl['amount']} {tpl['currency']}"))
        def use_selected():
            sel = tree.selection()
            if not sel: return
            idx = tree.index(sel[0])
            tpld = data['templates'][idx]
            self.open_add(template=Template(**{k:tpld[k] for k in tpld}))
        def delete_selected():
            sel = tree.selection();
            if not sel: return
            if messagebox.askyesno('Delete','Delete selected template?'):
                idx = tree.index(sel[0]); data['templates'].pop(idx); save_data(); win.destroy()
        tk.Button(win, text='Use', command=use_selected).pack(side='left', padx=4, pady=4)
        tk.Button(win, text='Delete', command=delete_selected).pack(side='left', padx=4)

    def open_budgets(self):
        win = tk.Toplevel(self); win.title('Budgets'); win.geometry('380x320')
        tree = ttk.Treeview(win, columns=('cat','amt'), show='headings')
        tree.heading('cat', text='Category'); tree.heading('amt', text='Monthly Budget (disp)')
        tree.pack(fill='both', expand=True)
        sym = currency_symbol()
        for cat, bud in data['budgets'].items():
            tree.insert('', 'end', values=(cat, f"{sym}{convert_from_base(bud):,.2f}"))
        cat_var = tk.StringVar(); amt_var = tk.StringVar()
        tk.Entry(win, textvariable=cat_var).pack(fill='x', padx=6, pady=2)
        tk.Entry(win, textvariable=amt_var).pack(fill='x', padx=6, pady=2)
        def add_or_update():
            try: amt = float(amt_var.get())
            except: return messagebox.showerror('Error','Invalid amount')
            data['budgets'][cat_var.get()] = round(convert_to_base(amt, data['settings']['display_currency']),2)
            save_data(); win.destroy(); self.refresh_all()
        tk.Button(win, text='Add/Update', command=add_or_update).pack(pady=4)

    def open_charts(self):
        if Figure is None:
            return messagebox.showinfo('Charts','Matplotlib not available.')
        win = tk.Toplevel(self); win.title('Charts'); win.geometry('920x600')
        nb = ttk.Notebook(win); nb.pack(fill='both', expand=True)
        # Prepare data
        trans = [t for t in data['transactions'] if current_month_filter(t)]
        days = {}
        income_total = 0; expense_total = 0
        for t in trans:
            d = t['date'][-2:]
            days.setdefault(d,0.0)
            if t['ttype']=='expense':
                days[d]-= t['amount_base']
                expense_total += t['amount_base']
            else:
                days[d]+= t['amount_base']
                income_total += t['amount_base']
        # Spending over time
        fig1 = Figure(figsize=(5,4), dpi=100)
        ax1 = fig1.add_subplot(111)
        x = sorted(days.keys())
        y = [convert_from_base(days[k]) for k in x]
        ax1.plot(x,y, marker='o', color='#b33b3b')
        ax1.set_title('Net Flow By Day (This Month)')
        ax1.set_xlabel('Day'); ax1.set_ylabel(currency_symbol())
        canvas1 = FigureCanvasTkAgg(fig1, master=nb)
        f1 = tk.Frame(nb); canvas1.get_tk_widget().pack(fill='both', expand=True); canvas1.draw()
        nb.add(f1, text='Daily Flow'); f1.update()

        # Expense breakdown pie
        cat_map = category_spend()
        fig2 = Figure(figsize=(5,4), dpi=100)
        ax2 = fig2.add_subplot(111)
        if cat_map:
            labels = list(cat_map.keys())
            sizes = [convert_from_base(v) for v in cat_map.values()]
            ax2.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#d16868','#b33b3b','#8f2f2f','#e28c8c','#c24d4d'])
            ax2.set_title('Expenses by Category')
        canvas2 = FigureCanvasTkAgg(fig2, master=nb)
        f2 = tk.Frame(nb); canvas2.get_tk_widget().pack(fill='both', expand=True); canvas2.draw(); nb.add(f2, text='Categories')

        # Income vs Expense
        fig3 = Figure(figsize=(5,4), dpi=100)
        ax3 = fig3.add_subplot(111)
        vals = [convert_from_base(income_total), convert_from_base(expense_total)]
        ax3.bar(['Income','Expenses'], vals, color=['#8f2f2f','#d16868'])
        ax3.set_ylabel(currency_symbol())
        ax3.set_title('Income vs Expenses (Month)')
        canvas3 = FigureCanvasTkAgg(fig3, master=nb)
        f3 = tk.Frame(nb); canvas3.get_tk_widget().pack(fill='both', expand=True); canvas3.draw(); nb.add(f3, text='Income vs Expense')

    def open_settings(self):
        win = tk.Toplevel(self); win.title('Settings'); win.geometry('360x360')
        rate_var = tk.StringVar(value=str(data['settings']['php_rate']))
        daily_var = tk.StringVar(value=data['settings']['daily_reminder_time'])
        weekly_day_var = tk.StringVar(value=data['settings']['weekly_reminder_day'])
        weekly_time_var = tk.StringVar(value=data['settings']['weekly_reminder_time'])
        for lbl, var in [('PHP Rate (1 USD = PHP)', rate_var), ('Daily Reminder (HH:MM)', daily_var), ('Weekly Day (Mon-Sun)', weekly_day_var), ('Weekly Time (HH:MM)', weekly_time_var)]:
            tk.Label(win, text=lbl).pack(); tk.Entry(win, textvariable=var).pack(fill='x', padx=6, pady=2)
        def save_settings():
            try:
                data['settings']['php_rate'] = float(rate_var.get())
            except: return messagebox.showerror('Error','Invalid PHP rate')
            data['settings']['daily_reminder_time']=daily_var.get()
            if weekly_day_var.get() in WEEKDAYS:
                data['settings']['weekly_reminder_day']=weekly_day_var.get()
            data['settings']['weekly_reminder_time']=weekly_time_var.get()
            save_data(); self.refresh_all(); win.destroy()
        tk.Button(win, text='Save', command=save_settings).pack(pady=6)

    def change_currency(self, _=None):
        data['settings']['display_currency']=self.currency_var.get(); save_data(); self.refresh_all()

    def toggle_theme(self):
        data['settings']['theme'] = 'dark' if data['settings']['theme']=='light' else 'light'
        save_data(); self.apply_theme()

    def delete_selected(self):
        sel = self.tr_tree.selection()
        if not sel: return
        if not messagebox.askyesno('Confirm','Delete selected transaction?'): return
        # Retrieve id directly from tree values
        tr_id = int(self.tr_tree.item(sel[0])['values'][0])
        data['transactions'] = [t for t in data['transactions'] if t['id'] != tr_id]
        save_data(); self.refresh_all()

    def edit_selected(self):
        sel = self.tr_tree.selection()
        if not sel: return
        tr_id = int(self.tr_tree.item(sel[0])['values'][0])
        tr = next((t for t in data['transactions'] if t['id']==tr_id), None)
        if not tr: return
        win = tk.Toplevel(self); win.title('Edit Transaction'); win.geometry('340x370')
        entries = {}
        def add_field(label, default=''):
            tk.Label(win, text=label).pack()
            var = tk.StringVar(value=default)
            ent = tk.Entry(win, textvariable=var); ent.pack(fill='x', padx=6)
            entries[label]=var
        add_field('Description', tr['description'])
        add_field('Category', tr['category'])
        add_field('Amount', str(tr['amount_orig']))
        tk.Label(win, text='Type').pack(); ttype_var = tk.StringVar(value=tr['ttype'])
        ttk.Combobox(win, textvariable=ttype_var, values=['expense','income']).pack(fill='x', padx=6)
        tk.Label(win, text='Currency').pack(); cur_var = tk.StringVar(value=tr['currency'])
        ttk.Combobox(win, textvariable=cur_var, values=['USD','PHP']).pack(fill='x', padx=6)
        tk.Label(win, text='Date (YYYY-MM-DD)').pack(); date_var = tk.StringVar(value=tr['date'])
        tk.Entry(win, textvariable=date_var).pack(fill='x', padx=6)
        def submit():
            # Validate amount
            try:
                amt = float(entries['Amount'].get())
            except Exception:
                return messagebox.showerror('Error','Invalid amount')
            # Update fields
            tr['description'] = entries['Description'].get()
            tr['category'] = entries['Category'].get()
            tr['ttype'] = ttype_var.get()
            tr['currency'] = cur_var.get()
            tr['amount_orig'] = amt
            tr['amount_base'] = round(convert_to_base(amt, cur_var.get()),2)
            # Date
            try:
                dt.date.fromisoformat(date_var.get())
                tr['date'] = date_var.get()
            except Exception:
                pass
            save_data(); self.refresh_all(); win.destroy()
        tk.Button(win, text='Save Changes', command=submit).pack(pady=10)

    # ---- Reminders ----
    def schedule_reminder_check(self):
        self.after(60*1000, self.schedule_reminder_check)  # re-schedule every minute
        self.check_reminders()

    def check_reminders(self):
        now = dt.datetime.now()
        # Daily reminder
        dr = data['settings'].get('daily_reminder_time','21:00')
        try:
            hh, mm = map(int, dr.split(':'))
            if now.hour==hh and now.minute==mm:
                messagebox.showinfo('Reminder','Log today\'s expenses!')
        except: pass
        # Weekly reminder
        wr_day = data['settings'].get('weekly_reminder_day','Sun')
        wr_time = data['settings'].get('weekly_reminder_time','21:00')
        try:
            hh, mm = map(int, wr_time.split(':'))
            if WEEKDAYS[now.weekday()]==wr_day and now.hour==hh and now.minute==mm:
                messagebox.showinfo('Weekly Reminder','Review your weekly spending and log missing entries.')
        except: pass

    # ---- Export ----
    def export_data(self):
        filetypes = [('CSV','*.csv')]
        if HAS_OPENPYXL:
            filetypes.append(('Excel','*.xlsx'))
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=filetypes)
        if not path: return
        if path.lower().endswith('.csv'):
            with open(path,'w',newline='',encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['id','date','type','category','description','amount_base(USD)','orig_amount','orig_currency'])
                for t in data['transactions']:
                    w.writerow([t['id'], t['date'], t['ttype'], t['category'], t['description'], t['amount_base'], t['amount_orig'], t['currency']])
            messagebox.showinfo('Export','CSV exported.')
        else:
            if not HAS_OPENPYXL:
                return messagebox.showerror('Missing','Install openpyxl for Excel export (pip install openpyxl).')
            wb = Workbook(); ws = wb.active; ws.append(['ID','Date','Type','Category','Description','Amount Base (USD)','Orig Amount','Orig Currency'])
            for t in data['transactions']:
                ws.append([t['id'], t['date'], t['ttype'], t['category'], t['description'], t['amount_base'], t['amount_orig'], t['currency']])
            wb.save(path); messagebox.showinfo('Export','Excel exported.')

    # ---- Import ----
    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[('CSV','*.csv')])
        if not path: return
        imported = 0
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    date = row.get('date') or dt.date.today().isoformat()
                    # accept date; if invalid skip
                    try: dt.date.fromisoformat(date)
                    except: continue
                    ttype = row.get('type','expense').lower()
                    if ttype not in ('income','expense'): continue
                    cat = row.get('category','General')
                    desc = row.get('description','')
                    cur = row.get('currency','USD').upper()
                    amt_raw = row.get('amount') or row.get('amount_orig') or ''
                    base_raw = row.get('amount_base') or row.get('amount_base(USD)') or ''
                    if amt_raw:
                        amt = float(amt_raw)
                        base = convert_to_base(amt, cur)
                    elif base_raw:
                        base = float(base_raw); amt = base if cur=='USD' else base*data['settings']['php_rate']
                    else:
                        continue
                    tid = data['next_id']; data['next_id']+=1
                    data['transactions'].append({
                        'id':tid,'date':date,'ttype':ttype,'category':cat,'description':desc,
                        'amount_base':round(base,2),'currency':cur,'amount_orig':amt
                    })
                    imported +=1
                except Exception:
                    continue
        save_data(); self.refresh_all(); messagebox.showinfo('Import', f'Imported {imported} transactions.')

    # ---- Filters ----
    def clear_filters(self):
        self.start_date_var.set(''); self.end_date_var.set(''); self.search_var.set(''); self.filter_type_var.set('All'); self.filter_category_var.set('All'); self.refresh_transactions()

    def apply_filters(self, items):
        sd = self.start_date_var.get().strip(); ed = self.end_date_var.get().strip()
        search = self.search_var.get().strip().lower()
        ftype = self.filter_type_var.get()
        fcat = self.filter_category_var.get()
        def date_ok(tdate):
            try: d = dt.date.fromisoformat(tdate)
            except: return True
            if sd:
                try: sdd = dt.date.fromisoformat(sd)
                except: sdd=None
                if sdd and d < sdd: return False
            if ed:
                try: edd = dt.date.fromisoformat(ed)
                except: edd=None
                if edd and d > edd: return False
            return True
        out = []
        for t in items:
            if ftype!='All' and t['ttype']!=ftype: continue
            if fcat!='All' and t['category']!=fcat: continue
            if search and search not in (t['description'] or '').lower() and search not in t['category'].lower(): continue
            if not date_ok(t['date']): continue
            out.append(t)
        return out

# --------------- Main ---------------
if __name__ == '__main__':
    data = load_data()
    app = BudgetApp()
    app.mainloop()
