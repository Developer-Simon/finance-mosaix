#!/usr/bin/env python3
"""
Finance Database Quick Start Script
Run from command line to import data and analyze finances
"""

import argparse
from pathlib import Path

try:
    from .db_schema import init_database, show_schema, get_connection
    from .import_transactions import FinanceImporter
    from .query_finance import print_balance_summary, print_category_summary, FinanceQueries
except ImportError:
    from db_schema import init_database, show_schema, get_connection
    from import_transactions import FinanceImporter
    from query_finance import print_balance_summary, print_category_summary, FinanceQueries


def default_db_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "finance.duckdb")


def main():
    parser = argparse.ArgumentParser(
        description="Personal Finance Database - Quick Start CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/finance_cli.py --init                           # Initialize database
  python src/finance_cli.py --import Sample.xlsx             # Import from Excel
  python src/finance_cli.py --balance                        # Show account balances
  python src/finance_cli.py --spending 30                    # Show last 30 days spending
  python src/finance_cli.py --schema                         # Show database schema
        """
    )

    parser.add_argument('--init', action='store_true', help='Initialize database')
    parser.add_argument('--import', dest='import_file', help='Import Excel file')
    parser.add_argument('--balance', action='store_true', help='Show account balances')
    parser.add_argument('--spending', type=int, default=30, help='Show spending for last N days (default: 30)')
    parser.add_argument('--schema', action='store_true', help='Show database schema')
    parser.add_argument('--search', help='Search transactions by description')
    parser.add_argument('--normalize', nargs='?', const='goods', choices=['goods'], help='Normalize derived values for a pool (currently goods only)')
    parser.add_argument('--item-name', help='Optional goods item name to limit normalization')
    parser.add_argument('--valuation-date', help='Optional goods valuation date to limit normalization (YYYY-MM-DD)')
    parser.add_argument('--what-if', action='store_true', help='Preview normalization without writing changes')
    parser.add_argument('--db', default=default_db_path(), help='Database path (default: finance.duckdb)')

    args = parser.parse_args()

    db_path = args.db

    if args.init:
        print(f"\n[INFO] Initializing database at: {db_path}")
        init_database(db_path)
        print("[OK] Database initialized!\n")

    if args.schema:
        show_schema(db_path)

    if args.import_file:
        if not Path(args.import_file).exists():
            print(f"[ERROR] File not found: {args.import_file}")
            return

        importer = FinanceImporter(args.import_file, db_path)
        importer.run()

    if args.normalize:
        if args.normalize != 'goods':
            print(f"[ERROR] Unsupported normalization pool: {args.normalize}")
            return

        queries = FinanceQueries(db_path)
        item_name = args.item_name
        valuation_date = args.valuation_date
        if item_name and valuation_date:
            print("[ERROR] Please provide either --item-name or --valuation-date, not both.")
            return

        if valuation_date:
            from datetime import date as _date
            try:
                valuation_date = _date.fromisoformat(valuation_date)
            except ValueError:
                print("[ERROR] Invalid valuation date format. Use YYYY-MM-DD.")
                return

        result = queries.normalize_goods_valuations(
            item_name=item_name,
            valuation_date=valuation_date,
            what_if=args.what_if,
        )

        if args.what_if:
            print("\n[INFO] Goods normalization preview")
        else:
            print("\n[INFO] Goods normalization executed")

        print(f"Processed rows: {result['rows_processed']}")
        print(f"Rows with recalculated derived values: {result['rows_changed']}")

        if result['rows_changed']:
            print("\nChanged rows:")
            for original, normalized in zip(result['original_rows'], result['normalized_rows']):
                if original[0] in result['changed_ids']:
                    print(
                        f"  Valuation ID {original[0]} | Item: {original[2]} | "
                        f"Value Change {original[6]} -> {normalized[6]} | "
                        f"Current Value {original[7]} -> {normalized[7]}"
                    )
        return

    if args.balance:
        queries = FinanceQueries(db_path)
        balances = queries.get_balance_by_account()

        print("\n" + "=" * 60)
        print("ACCOUNT BALANCES")
        print("=" * 60 + "\n")

        total = 0
        for account, balance, last_tx in balances:
            if balance:
                print(f"  {account:<30} EUR {balance:>12,.2f}  (Last: {last_tx})")
                total += balance

        print("-" * 60)
        print(f"  {'TOTAL':<30} EUR {total:>12,.2f}\n")

    if args.spending:
        from datetime import datetime, timedelta
        queries = FinanceQueries(db_path)
        categories = queries.get_spending_by_category(
            start_date=datetime.now().date() - timedelta(days=args.spending)
        )

        print(f"\n" + "=" * 60)
        print(f"SPENDING (Last {args.spending} days)")
        print("=" * 60 + "\n")

        total = 0
        for cat, count, amount, avg in categories:
            print(f"  {cat:<30} EUR {amount:>10,.2f}  ({count} tx)")
            total += amount

        print("-" * 60)
        print(f"  {'TOTAL':<30} EUR {total:>10,.2f}\n")

    if args.search:
        queries = FinanceQueries(db_path)
        results = queries.search_transactions(args.search)

        if results:
            print(f"\n[INFO] Found {len(results)} transactions matching '{args.search}':\n")
            for tx_id, description, category, amount, date, account in results:
                print(f"  {date} | {account:<15} | {category:<20} | EUR {amount:>10,.2f} | {description}")
        else:
            print(f"\n[INFO] No transactions found matching '{args.search}'")

    if not any([args.init, args.import_file, args.balance, args.schema, args.search]) and args.spending == 30:
        parser.print_help()


if __name__ == '__main__':
    main()
