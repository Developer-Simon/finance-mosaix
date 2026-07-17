# Dashboard Charts and Metrics Status

## Current dashboard state
- Home page: timeline and latest pool distribution snapshot.
- Charts page: native charts for Timeline, Spending, Balances, Income vs Expenses, Transaction Frequency, Average Transaction, Stock Positions, Goods Valuation, and Interest Balances.
- Metrics page: new navigation entry with separate metrics sections for Overview, Cash Flow, Category, Account, Portfolio, Goods & Interest, and Data Health.

## Metrics page implementation audit
- Overview Metrics: implemented with latest total net worth and pool totals from the combined timeline.
- Cash Flow Metrics: implemented with total income, total expenses, net income, expense ratio, and average monthly expense based on database date range.
- Category Metrics: implemented with top spending category, top 10 expense categories, category counts, and uncategorized transaction count.
- Account Metrics: implemented with total account balance, top and lowest account, and current account balance table.
- Portfolio Metrics: implemented with total stock, goods, and interest values plus top stock positions and top goods by current value.
- Goods & Interest Metrics: implemented with aggregated goods value/change and interest value/delta counts.
- Data Health Metrics: implemented with database coverage range, latest import timestamp, row counts, and missing category diagnostics.

## Partial coverage
- Pool allocation trend as percentage remains absent.
- Per-account historical balance trends are not yet present.
- Stock gainers/losers ranking is not a dedicated chart.
- Goods depreciation over time and interest growth trends are not yet charted.
- Monthly cashflow / income-expense trend charts are not implemented on the metrics page.

## Ideas
### Chart ideas
- Add stock gainers/losers ranking chart for the portfolio.
- Add pool allocation percentage metric and trending allocation summary.
- Add goods depreciation waterfall / loss contribution visualization.
- Add interest growth rate and earnings momentum chart.
- Add savings versus spending cumulative trend chart.
- Add account volatility / balance stability heatmap.

### Metrics ideas
- Add a dedicated pool allocation percentage metric.
- Add per-account trend analytics and account health scoring.
- Add stock gainers/losers rankings and weighted portfolio delta.
- Add goods depreciation totals, average change, and trend metrics.
- Add interest earned totals, growth rate, and periodic delta metrics.
- Add data health flags for stale imports, missing categories, and date range gaps.

## Implemented charts
- Asset Allocation Trend chart shows normalized pool allocation over time.
- Cash Flow Trend chart shows monthly income vs expense history and net flow.
- Category Drill-down chart supports top main categories and subcategory breakdown.
- Account Balance History chart shows selectable account balance trends.
- Stock Portfolio Performance chart shows stock portfolio total value over snapshots.
- Goods Valuation Change chart shows goods current value history by item or aggregate.
- Interest Growth chart shows interest balance history for selected accounts or aggregate.

## Existing charts
- Timeline
- Spending
- Balances
- Income vs Expenses
- Transaction Frequency
- Average Transaction
- Asset Allocation Trend
- Cash Flow Trend
- Category Drill-down
- Account Balance History
- Stock Portfolio Performance
- Goods Valuation Change
- Interest Growth
- Stock Positions
- Goods Valuation
- Balance with Delta
