# Budget Tracker (Python, Single-File) v1.1.0

A compact yet feature-rich personal budget tracker built entirely with standard Python + Tkinter and (optionally) Matplotlib for charts. Version 1.1 introduces a modernized, more responsive UI with filtering, editing, and CSV import while preserving the soft red light/dark theme.

## Author & Copyright
(c) 2025 John Marc Gonzales. All Rights Reserved.

## Key Features
Core (v1.0 + v1.1):
- Dual Currency: USD (base) & PHP (display toggle) with adjustable exchange rate.
- Light & Dark Modes: Soft red theme toggle (soft, non-harsh palette).
- Income & Expense Tracking: Categorized with descriptions.
- Edit Transactions: Inline selection + edit dialog (v1.1).
- Filters & Search (v1.1): Date range, type, category, live text search.
- Category Budgets: Set monthly limits per category; shows remaining & over/under status.
- Remaining Budget: Prominent summary across all categories.
- Visual Overview (Requires Matplotlib):
  - Net daily flow line chart
  - Expenses by category pie chart
  - Income vs expenses bar chart
- Quick Add Popup: Fast minimal entry form.
- Transaction Templates: Save & reuse common entries (e.g., "Weekly Groceries").
- CSV Import (v1.1): date,type,category,description,amount,currency (+ amount_base fallback).
- Data Export: CSV (always) & Excel (.xlsx with `openpyxl`).
- Data Entry Reminders: Daily & weekly popup reminders inside the running app.
- Responsive Layout (v1.1): Paned window, resizable transaction list, card-style metrics.
- Persistent Storage: All data saved to `data.json` (transactions, budgets, settings, templates).
- Compact Code: Entire logic in `main.py` (easy to read & modify).

## Requirements
- Python 3.9+ (tested on 3.11)
- Core functionality uses only the Python standard library (Tkinter, json, csv, etc.).
- Optional extras:
  - `matplotlib` (charts)
  - `openpyxl` (Excel export)

### Quick Install (all optional features)
```bash
pip install -r requirements.txt
```

### Minimal Run (no optional packages)
Just run the app; it will gracefully hide charts / Excel export if dependencies are missing.

### Manual Install (pick specific extras)
```bash
pip install matplotlib
pip install openpyxl
```
You may install only the packages you need.

## Running
```bash
python main.py
```
A window will open. Use the top bar buttons to add transactions, manage budgets, view charts, export, and toggle theme.

## Data File
`data.json` is created automatically in the same folder. Safe to back up or transfer.

## Currency Handling
- Internal base currency: USD stored as `amount_base`.
- Display currency toggled between USD / PHP.
- Edit PHP rate in Settings (default 58.0) to reflect current exchange.

## Reminders
The app checks every minute. Configure times (24h `HH:MM`) and weekly day (Mon-Sun) in Settings. Reminders appear only while the app is open.

## Export
- CSV: Always available.
- Excel: Requires `openpyxl`; pick `.xlsx` in the save dialog.

## Templates
1. Add a transaction (uncheck Quick Add).
2. Tick "Save as Template".
3. Reuse via Templates > Use.

## Budgets & Remaining
Set per-category monthly budgets. Overview shows each category remaining (negative if over). Aggregate "Remaining Total Budget" uses sum of category budgets minus total expenses of those categories for the month.

## Compact Design Philosophy
All in one file for easy portability. For scaling, consider refactoring into packages (models, services, UI, persistence).

## License
Custom permissive license in `LICENSE`. Summary:
- Free to use, modify, and distribute with attribution to "John Marc Gonzales".
- Include the copyright & license text in redistributions.
- Significant added value required to sell as a standalone product.
- No endorsement or use of author name/likeness without permission.

This README section is an informal summary; the full license text governs.

## Roadmap Ideas (Not Implemented Yet)
- Password / encryption
- Multi-file modular refactor
- Recurring transaction automation
- Cloud sync / backup

## Support
Feel free to extend. Credit the original author as required.

Enjoy managing your finances more clearly! 🚀
