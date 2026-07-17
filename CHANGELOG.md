# Changelog

All notable changes to this project will be documented in this file.

# [0.2.0](https://github.com/Developer-Simon/finance-mosaix/releases/tag/v0.2.0) - 2026-07-15

### Features

- Add onboarding support and improved documentation for the finance dashboard.

### Fixes

- Fix timeline query to include latest values on dates without snapshots.

# [0.1.0](https://github.com/Developer-Simon/finance-mosaix/releases/tag/v0.1.0) - 2026-07-14

### Features

- Add history and skip support.
- Add auto skipping based on history.
- Add finance database tool.
- Add Streamlit application for the finance database.
- Make the dashboard start script open the browser and terminate with the terminal session.
- Add table visualizations.
- Create a data edit visualization.
- Add all pools to the timeline.
- Add a main function menu.
- Add merge tool support for Accounts.
- Add diff viewer for merge editor changes.
- Extend the merge editor to work across all data pools.
- Extend the data editor to select from all pools.
- Add selection to the merge editor diff table.
- Add the data creator.
- Prefill existing stock data in the data creator.
- Update the former pyplot timeline to a native Streamlit plot.
- Add a native spending chart.
- Update the goods data creator to use prefilled tables.
- Add data normalization for goods.
- Add account balances as a common balance base and monitoring tool.
- Add total line and logarithmic scale to the timeline chart.
- Add a settings page with software info details.
- Introduce a home page for quick data overview.
- Add application modes for simpler and expert function display.
- Add a balances chart.
- Add charts from the legacy pyplot implementation.
- Add full chart coverage for the dashboard.
- Add pool selection for charts.
- Add a metrics page for monthly pool summaries.
- Add an ignore option for notifications.
- Add ability to change stock quantity in the stocks data creator.
- Make the stocks data creator fetch information near the snapshot date.
- Add filter support for zero balances.

### Fixes

- Fix spending visualization issues.
- Fix euro-to-dollar conversion and selector visibility.
- Fix account detection when the account is not working.
- Fix goods depreciation calculation in the data creator.
- Fix current value import for goods in the import tool.
- Fix interest data creator IDs not being applied.
- Fix data organizer cash creation flow.
- Fix the data organizer preview for cash-derived balances.
- Fix renamed Export mode to Expert mode.
- Fix settings not applying to the home page.
- Fix account balances selection and creation in the data creator.
- Fix prefilled values in the data creator.
- Fix restoration of pyplot charts.
- Fix the broken stocks position query.
- Fix the import mechanism to catch the "sparen" term.
- Fix database connection closure while the app is running.
- Fix previous price sourcing for stocks in the data creator.
- Fix stocks quantity updates in the data creator.
