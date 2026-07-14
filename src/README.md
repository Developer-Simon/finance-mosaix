# Personal Finance Database Setup

A lightweight DuckDB-based personal finance tracking system for daily transactions, assets, and investments.

## 📋 Database Structure

The database uses a **normalized, long-format schema** with the following tables:

### Core Tables
- **accounts**: Bank/savings accounts with multiple currency support
- **categories**: Spending categories (income, expenses, transfers)
- **transactions**: Normalized transactions (one row per transaction-category pair)
- **balances_snapshot**: Monthly balance snapshots for history tracking

### Asset Tables
- **stocks**: Investment tracking (ticker, quantity, purchase price, current price)
- **goods**: Physical assets (with linear depreciation tracking)
- **goods_depreciation_log**: Depreciation history for assets

## 🚀 Quick Start

### 1. Initialize Database
```python
from db_schema import init_database

db = init_database("finance.duckdb")
```

### 2. Import Transactions from Excel
```python
from import_transactions import FinanceImporter

importer = FinanceImporter("Sample.xlsx")
importer.run()
```

The import tool will:
- Show available sheets
- Let you select a sheet to import
- Create or select an account
- Auto-detect date from sheet name (or enter manually)
- Normalize wide Excel format → long database format
- Insert all transactions

### 3. Query Your Data
```python
from query_finance import FinanceQueries

queries = FinanceQueries()

# Get all account balances
balances = queries.get_balance_by_account()

# Get spending by category (last 30 days)
categories = queries.get_spending_by_category()

# Search transactions
results = queries.search_transactions("rent")

# Print summaries
from query_finance import print_balance_summary, print_category_summary
print_balance_summary()
print_category_summary(30)
```

### 4. Asset Depreciation
```python
from query_finance import DepreciationCalculator

calc = DepreciationCalculator()

# Calculate depreciated value of an asset
result = calc.calculate_linear_depreciation(good_id=1)
print(f"Current value: €{result['current_value']:.2f}")

# Update good's current value and log depreciation
calc.update_good_valuation(good_id=1)

# Get valuation for all goods
all_goods = calc.get_all_goods_valuation()
print(f"Total assets value: €{all_goods['total_value']:.2f}")
```

## 📊 Data Format (Excel Import)

The importer expects Excel sheets with:
- **Row 1**: Headers (transaction number, description, categories, balance, account)
- **Rows 2+**: Transaction data
- **Wide format**: One transaction per row, with amounts in category columns

Example:
| Nr. | Bezeichnung | Einnahmen | Investment | ... | Cash | Account |
|-----|-------------|-----------|------------|-----|------|---------|
| 1 | Gehalt | 3000 | | | 31500 | COMDIRECT |
| 2 | Versicherung | | -50 | | 31450 | COMDIRECT |

## 🔄 Import Workflow

1. **Sheet Selection**: Choose which sheet to import
2. **Account Selection**: Pick existing account or create new one
3. **Date Handling**: Auto-detect from sheet name or enter manually
4. **Normalization**: Convert wide → long format automatically
5. **Summary**: Show all imported transactions by category

## 📈 Usage Patterns

### Monthly Imports
- Create new sheet for each month (e.g., "August 2025")
- Run import tool, select sheet, auto-detects month/year
- Transactions append to existing database (no duplicates)

### Analysis
- Query spending trends by category
- Compare income vs. expenses
- Track asset depreciation over time
- View balance history

### Asset Tracking
- Add items to `goods` table with purchase price and depreciation rate
- Linear depreciation: annual_depreciation = (price × rate%) / 100
- Automatic valuation calculations
- Full depreciation history logged

## 🛠️ Files

- `src/db_schema.py` - Database initialization and schema
- `src/import_transactions.py` - Excel import tool with interactive prompts
- `src/query_finance.py` - Query helpers and depreciation calculator
- `finance.duckdb` - The actual database file (created on first run)

## 💡 Tips

- Database file (`finance.duckdb`) is **portable** - copy to Linux and it works
- **No server needed** - completely offline
- **Backward compatible** - schema handles schema migration
- **Flexible categories** - auto-creates categories from Excel headers
- **Multiple accounts** - fully supported with cross-transfers

## 🔧 Next Steps

1. Run `python src/finance_cli.py --import Sample.xlsx` to import the workbook
2. Use `python src/finance_cli.py --balance` or `python src/finance_cli.py --search ...` to explore your data
3. Create analysis notebook (see `DataVisualisation.ipynb`)
4. Add stocks and goods as needed

---

**Platform Support**: Windows, Linux, macOS (identical database files)
