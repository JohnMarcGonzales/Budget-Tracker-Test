# Budget Tracker (Python, Single-File)

A compact yet feature-rich personal budget tracker built entirely with standard Python + Tkinter and (optionally) Matplotlib for charts. Designed with a soft red light/dark theme and focused on simplicity.

## Author & Copyright
(c) 2025 John Marc Gonzales. All Rights Reserved.

## Key Features
- Dual Currency: USD (base) & PHP (display toggle) with adjustable exchange rate.
- Light & Dark Modes: Soft red theme toggle.
- Income & Expense Tracking: Categorized with descriptions.
- Category Budgets: Set monthly limits per category; shows remaining & over/under status.
- Remaining Budget: Prominent monthly remaining summary across all categories.
- Visual Overview (Requires Matplotlib):
  - Net daily flow line chart
  - Expenses by category pie chart
  - Income vs expenses bar chart
- Quick Add Popup: Fast minimal entry form.
- Transaction Templates: Save & reuse common entries (e.g., "Weekly Groceries").
- Data Export: CSV (always) & Excel (.xlsx with `openpyxl`).
- Data Entry Reminders: Daily & weekly popup reminders inside the running app.
- Persistent Storage: All data saved to `data.json` (transactions, budgets, settings, templates).
- Compact Code: Entire logic in `main.py` (easy to read & modify).

## Requirements
- Python 3.9+ (Tested on 3.11)
- Standard library only for core usage.
- Optional (for charts):
  - `matplotlib`
  - `openpyxl` (only if you want Excel export)

Install optional packages:
```bash
pip install matplotlib openpyxl
```
(You can skip them if you don't need charts or Excel export; the app will still run.)

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
See `LICENSE` (custom permissive license retaining author credit notice requirement).

## Roadmap Ideas (Not Implemented)
- Filtering by custom date range
- Editing existing transactions
- Import from CSV
- Password / encryption

## Support
Feel free to extend. Credit the original author as required.

Enjoy managing your finances more clearly! 🚀
