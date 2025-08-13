#!/usr/bin/env python3
"""
Compact Budget Tracker
Author: John Marc Gonzales (c) 2025

Features:
 - USD & PHP currency support (simple adjustable rate)
 - Light/Dark soft red themed UI (toggle)
 - Track income & expenses with categories
 - Monthly category budgets; shows Remaining & Over/Under
 - Visualizations (Matplotlib):
     * Spending over current month (line)
     * Expenses by category (pie)
     * Income vs Expenses (bar)
 - Quick Add pop-up
 - Transaction Templates (save/apply)
 - Export to CSV / Excel (.xlsx) without heavy deps (openpyxl optional)
 - Data Entry Reminders (daily + weekly) via app pop-ups
 - Single-file implementation for simplicity
 - Data persisted to JSON (transactions, budgets, settings, templates)

Notes:
 - Keep code compact; some compromises on separation of concerns.
 - For larger apps, split into modules & add proper MVC structure.
"""
import json, os, csv, datetime as dt, threading
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from math import fsum

# Matplotlib embedding
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception as e:  # Fallback placeholder
    Figure = None

DATA_FILE = 'data.json'
VERSION = '1.0.0'

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

def current_month_filter(tr: Transaction) -> bool:
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
        self.title('Budget Tracker - John Marc Gonzales')
        self.geometry('1100x700')
        self.minsize(1000,650)
        self.style = ttk.Style(self)
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
        self.top_bar = tk.Frame(self)
        self.top_bar.pack(fill='x')
        self.left_panel = tk.Frame(self)
        self.left_panel.pack(side='left', fill='y')
        self.main_panel = tk.Frame(self)
        self.main_panel.pack(side='left', fill='both', expand=True)
        self.stats_bar = tk.Frame(self)
        self.stats_bar.pack(fill='x')

        # Top bar controls
        tk.Button(self.top_bar, text='Add', command=self.open_add).pack(side='left', padx=4, pady=4)
        tk.Button(self.top_bar, text='Quick Add', command=lambda: self.open_add(quick=True)).pack(side='left', padx=4)
        tk.Button(self.top_bar, text='Templates', command=self.open_templates).pack(side='left', padx=4)
        tk.Button(self.top_bar, text='Budgets', command=self.open_budgets).pack(side='left', padx=4)
        tk.Button(self.top_bar, text='Charts', command=self.open_charts).pack(side='left', padx=4)
        tk.Button(self.top_bar, text='Export', command=self.export_data).pack(side='left', padx=4)
        tk.Button(self.top_bar, text='Settings', command=self.open_settings).pack(side='left', padx=4)
        tk.Button(self.top_bar, text='Theme', command=self.toggle_theme).pack(side='left', padx=4)
        tk.Label(self.top_bar, text='Currency:').pack(side='left')
        self.currency_var = tk.StringVar(value=data['settings']['display_currency'])
        tk.OptionMenu(self.top_bar, self.currency_var, 'USD','PHP', command=self.change_currency).pack(side='left')
        tk.Label(self.top_bar, text='v'+VERSION).pack(side='right', padx=8)

        # Left panel: Transactions list
        self.tr_tree = ttk.Treeview(self.left_panel, columns=('date','type','cat','desc','amt'), show='headings', height=25)
        for c, w in [('date',90),('type',60),('cat',100),('desc',150),('amt',90)]:
            self.tr_tree.heading(c, text=c.title())
            self.tr_tree.column(c, width=w, anchor='w')
        self.tr_tree.pack(fill='both', expand=True, padx=4, pady=4)
        tk.Button(self.left_panel, text='Delete Selected', command=self.delete_selected).pack(fill='x', padx=4, pady=2)

        # Main panel: Overview labels placeholder
        self.overview_frame = tk.Frame(self.main_panel)
        self.overview_frame.pack(fill='both', expand=True)
        self.income_lbl = self._dyn_label(self.overview_frame)
        self.expense_lbl = self._dyn_label(self.overview_frame)
        self.remaining_lbl = tk.Label(self.overview_frame, font=('Arial', 18,'bold'))
        self.remaining_lbl.pack(pady=10)
        self.budget_summary = self._dyn_label(self.overview_frame)
        tk.Label(self.overview_frame, text='(c) John Marc Gonzales', font=('Arial',9,'italic')).pack(side='bottom', pady=4)

    def _dyn_label(self, parent):
        lbl = tk.Label(parent, font=('Arial', 12))
        lbl.pack(pady=4)
        self.dynamic_labels.append(lbl)
        return lbl

    # ---- Data Refresh ----
    def refresh_all(self):
        self.refresh_transactions()
        self.refresh_overview()

    def refresh_transactions(self):
        for i in self.tr_tree.get_children():
            self.tr_tree.delete(i)
        sym = currency_symbol()
        for t in reversed(list_transactions()[-400:]):  # show last 400
            disp_amt = convert_from_base(t['amount_base'])
            self.tr_tree.insert('', 'end', values=(t['date'], t['ttype'], t['category'], t['description'], f"{sym}{disp_amt:,.2f}"))

    def refresh_overview(self):
        inc, exp = monthly_totals()
        sym = currency_symbol()
        self.income_lbl.config(text=f"Monthly Income: {sym}{convert_from_base(inc):,.2f}")
        self.expense_lbl.config(text=f"Monthly Expenses: {sym}{convert_from_base(exp):,.2f}")
        rem = remaining_budget()
        self.remaining_lbl.config(text=f"Remaining Total Budget: {sym}{convert_from_base(rem):,.2f}")
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
        idx_disp = self.tr_tree.index(sel[0])
        # Convert displayed index (reversed) to actual index
        actual_list = list_transactions()[-400:]
        actual = actual_list[::-1][idx_disp]
        # Remove by id
        data['transactions'] = [t for t in data['transactions'] if t['id'] != actual['id']]
        save_data(); self.refresh_all()

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
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv'),('Excel','*.xlsx')])
        if not path: return
        if path.lower().endswith('.csv'):
            with open(path,'w',newline='',encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['id','date','type','category','description','amount_base(USD)','orig_amount','orig_currency'])
                for t in data['transactions']:
                    w.writerow([t['id'], t['date'], t['ttype'], t['category'], t['description'], t['amount_base'], t['amount_orig'], t['currency']])
            messagebox.showinfo('Export','CSV exported.')
        else:
            try:
                from openpyxl import Workbook
            except ImportError:
                return messagebox.showerror('Missing','Install openpyxl for Excel export.')
            wb = Workbook(); ws = wb.active; ws.append(['ID','Date','Type','Category','Description','Amount Base (USD)','Orig Amount','Orig Currency'])
            for t in data['transactions']:
                ws.append([t['id'], t['date'], t['ttype'], t['category'], t['description'], t['amount_base'], t['amount_orig'], t['currency']])
            wb.save(path); messagebox.showinfo('Export','Excel exported.')

# --------------- Main ---------------
if __name__ == '__main__':
    data = load_data()
    app = BudgetApp()
    app.mainloop()
