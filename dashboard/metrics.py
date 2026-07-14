import pandas as pd
import streamlit as st


def _format_currency(value):
    try:
        return f"€{float(value):,.2f}"
    except Exception:
        return "€0.00"


def _safe_float(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _render_overview_metrics(queries):
    st.subheader("Overview Metrics")
    timeline = queries.get_all_pools_timeline()
    if not timeline:
        st.warning("No timeline data available to compute overview metrics.")
        return

    df = pd.DataFrame(timeline, columns=["Date", "Cash", "Stocks", "Goods", "Interest"])
    df["Date"] = pd.to_datetime(df["Date"])
    latest = df.sort_values("Date").iloc[-1]
    total_value = _safe_float(latest["Cash"]) + _safe_float(latest["Stocks"]) + _safe_float(latest["Goods"]) + _safe_float(latest["Interest"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Net Worth", _format_currency(total_value))
    col2.metric("Cash Value", _format_currency(latest["Cash"]))
    col3.metric("Stock Value", _format_currency(latest["Stocks"]))
    col4.metric("Goods Value", _format_currency(latest["Goods"]))

    st.metric("Interest Value", _format_currency(latest["Interest"]))
    st.write("**Latest Snapshot Date:**", latest["Date"].date())


def _render_cash_flow_metrics(queries):
    st.subheader("Cash Flow Metrics")
    income = _safe_float(queries.get_total_income())
    expenses = abs(_safe_float(queries.get_total_expenses()))
    net = income - expenses

    min_date, max_date = queries.get_database_date_range()
    months = None
    if min_date and max_date:
        days = (pd.to_datetime(max_date) - pd.to_datetime(min_date)).days
        months = max(int(days / 30), 1)

    monthly_avg_expense = expenses / months if months else 0.0
    expense_ratio = (expenses / income) if income else None

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", _format_currency(income))
    col2.metric("Total Expenses", _format_currency(expenses))
    col3.metric("Net Income", _format_currency(net))

    if expense_ratio is not None:
        st.metric("Expense Ratio", f"{expense_ratio:.2f}")
    else:
        st.metric("Expense Ratio", "N/A")

    st.metric("Average Monthly Expense", _format_currency(monthly_avg_expense))
    if months is not None:
        st.write(f"Data period: {min_date} to {max_date} ({months} months)")


def _render_category_metrics(queries):
    st.subheader("Category Metrics")
    categories = queries.get_spending_by_category()
    if not categories:
        st.warning("No category spending data available.")
        return

    df = pd.DataFrame(categories, columns=["Category", "Count", "Amount", "Average"])
    df["Amount"] = df["Amount"].abs().astype(float)
    df = df.sort_values("Amount", ascending=False)
    top_category = df.iloc[0]["Category"] if not df.empty else "N/A"
    top_amount = df.iloc[0]["Amount"] if not df.empty else 0.0

    st.metric("Top Spending Category", top_category)
    st.metric("Top Category Spend", _format_currency(top_amount))
    st.metric("Number of Expense Categories", len(df))
    st.markdown("**Top 10 Expense Categories**")
    st.table(df.head(10).reset_index(drop=True))

    uncategorized_count = queries.conn.execute(
        "SELECT COUNT(*) FROM cash_transactions t LEFT JOIN categories c ON t.category_id = c.category_id WHERE c.category_id IS NULL"
    ).fetchone()[0]
    st.write("Uncategorized transactions:", int(uncategorized_count))


def _render_account_metrics(queries):
    st.subheader("Account Metrics")
    balances = queries.get_balance_by_account()
    if not balances:
        st.warning("No account balances available.")
        return

    df = pd.DataFrame(balances, columns=["Account", "Balance", "Last Transaction"])
    df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce").fillna(0.0)
    total_balance = df["Balance"].sum()
    top_account = df.sort_values("Balance", ascending=False).iloc[0]["Account"]
    bottom_account = df.sort_values("Balance", ascending=True).iloc[0]["Account"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Account Balance", _format_currency(total_balance))
    col2.metric("Top Account", top_account)
    col3.metric("Lowest Account", bottom_account)

    st.markdown("**Accounts by current balance**")
    st.table(df.sort_values("Balance", ascending=False).reset_index(drop=True))


def _render_portfolio_metrics(queries):
    st.subheader("Portfolio Metrics")
    stock_positions = queries.stock.get_latest_stock_positions()
    goods_values = queries.goods.get_latest_goods_valuations()
    interest_balances = queries.interest.get_latest_interest_balances()

    total_stock = sum(_safe_float(row[4]) for row in stock_positions) if stock_positions else 0.0
    total_goods = sum(_safe_float(row[2]) for row in goods_values) if goods_values else 0.0
    total_interest = sum(_safe_float(row[2]) for row in interest_balances) if interest_balances else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Stock Portfolio Value", _format_currency(total_stock))
    col2.metric("Goods Current Value", _format_currency(total_goods))
    col3.metric("Interest Balance Total", _format_currency(total_interest))

    if stock_positions:
        top_stocks = pd.DataFrame(stock_positions, columns=["Name", "Ticker", "Quantity", "Price", "Position Value", "Delta Value", "Delta Percent"])
        top_stocks["Position Value"] = pd.to_numeric(top_stocks["Position Value"], errors="coerce").fillna(0.0)
        st.markdown("**Top Stock Positions**")
        st.table(top_stocks.sort_values("Position Value", ascending=False).head(10).reset_index(drop=True))

    if goods_values:
        goods_df = pd.DataFrame(goods_values, columns=["Item", "Purchase Value", "Current Value", "Value Change"])
        goods_df["Current Value"] = pd.to_numeric(goods_df["Current Value"], errors="coerce").fillna(0.0)
        st.markdown("**Top Goods by Current Value**")
        st.table(goods_df.sort_values("Current Value", ascending=False).head(10).reset_index(drop=True))


def _render_goods_interest_metrics(queries):
    st.subheader("Goods & Interest Metrics")
    goods_values = queries.goods.get_latest_goods_valuations()
    interest_balances = queries.interest.get_latest_interest_balances()

    total_goods = sum(_safe_float(row[2]) for row in goods_values) if goods_values else 0.0
    total_goods_change = sum(_safe_float(row[3]) for row in goods_values) if goods_values else 0.0
    total_interest = sum(_safe_float(row[2]) for row in interest_balances) if interest_balances else 0.0
    total_interest_delta = sum(_safe_float(row[4]) for row in interest_balances) if interest_balances else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Goods Value", _format_currency(total_goods))
    col2.metric("Total Goods Change", _format_currency(total_goods_change))
    col3.metric("Total Interest Value", _format_currency(total_interest))
    col4.metric("Total Interest Delta", _format_currency(total_interest_delta))

    st.write("Tracked goods items:", len(goods_values))
    st.write("Tracked interest accounts:", len(interest_balances))


def _render_data_health_metrics(queries):
    st.subheader("Data Health Metrics")
    min_date, max_date = queries.get_database_date_range()
    if min_date is None or max_date is None:
        st.warning("Unable to determine database date range.")
        return

    import_date = queries.conn.execute(
        "SELECT MAX(latest) FROM (SELECT MAX(import_date) AS latest FROM cash_transactions UNION ALL SELECT MAX(import_date) FROM stock_positions UNION ALL SELECT MAX(import_date) FROM goods_valuations UNION ALL SELECT MAX(import_date) FROM interest_balance_changes UNION ALL SELECT MAX(import_date) FROM account_balances)"
    ).fetchone()[0]

    total_transactions = queries.conn.execute("SELECT COUNT(*) FROM cash_transactions").fetchone()[0]
    total_stock_rows = queries.conn.execute("SELECT COUNT(*) FROM stock_positions").fetchone()[0]
    total_goods_rows = queries.conn.execute("SELECT COUNT(*) FROM goods_valuations").fetchone()[0]
    total_interest_rows = queries.conn.execute("SELECT COUNT(*) FROM interest_balance_changes").fetchone()[0]
    total_balance_rows = queries.conn.execute("SELECT COUNT(*) FROM account_balances").fetchone()[0]

    st.metric("Database range", f"{min_date} → {max_date}")
    st.metric("Latest import", import_date.strftime("%Y-%m-%d %H:%M:%S") if import_date else "Unknown")
    st.metric("Cash transactions", f"{total_transactions:,}")
    st.metric("Stock snapshots", f"{total_stock_rows:,}")
    st.metric("Goods valuations", f"{total_goods_rows:,}")
    st.metric("Interest rows", f"{total_interest_rows:,}")
    st.metric("Balance rows", f"{total_balance_rows:,}")

    missing_categories = queries.conn.execute(
        "SELECT COUNT(*) FROM cash_transactions t LEFT JOIN categories c ON t.category_id = c.category_id WHERE c.category_id IS NULL"
    ).fetchone()[0]
    st.write("Missing or invalid categories:", int(missing_categories))


def _render_pool_monthly_metrics(queries):
    st.subheader("Pool Monthly Summary")
    min_date, max_date = queries.get_database_date_range()
    if min_date is None or max_date is None:
        st.warning("Unable to determine database date range.")
        return

    timeline = queries.get_all_pools_timeline(start_date=min_date, end_date=max_date)
    if not timeline:
        st.warning("No pool timeline data available to compute monthly metrics.")
        return

    df = pd.DataFrame(timeline, columns=["Date", "Cash", "Stocks", "Goods", "Interest"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()

    numeric_cols = ["Cash", "Stocks", "Goods", "Interest"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    monthly_close = (
        df.sort_values(["Month", "Date"])
        .groupby("Month", as_index=False)
        .last()
        .drop(columns=["Date"])
    )
    monthly_close["Total"] = monthly_close.loc[:, numeric_cols].sum(axis=1)

    for pool in ["Cash", "Stocks", "Goods", "Interest", "Total"]:
        monthly_close[f"{pool} Diff"] = monthly_close[pool].diff().fillna(0.0)

    monthly_close["Month"] = monthly_close["Month"].dt.strftime("%Y-%m")
    monthly_close = monthly_close[
        ["Month", "Cash", "Cash Diff", "Stocks", "Stocks Diff", "Goods", "Goods Diff", "Interest", "Interest Diff", "Total", "Total Diff"]
    ]

    monthly_close = monthly_close.reset_index(drop=True)
    st.write(
        "This table shows the closing balance for each pool at the end of each month, plus the month-over-month change."
    )
    st.dataframe(
        monthly_close.style.format({
            "Cash": "€{:.2f}",
            "Cash Diff": "€{:.2f}",
            "Stocks": "€{:.2f}",
            "Stocks Diff": "€{:.2f}",
            "Goods": "€{:.2f}",
            "Goods Diff": "€{:.2f}",
            "Interest": "€{:.2f}",
            "Interest Diff": "€{:.2f}",
            "Total": "€{:.2f}",
            "Total Diff": "€{:.2f}",
        }),
        # selection_mode="multi-row",
        # selection_default={"selection": {"rows": list(range(len(monthly_close)))}},
        # on_select=lambda: None,
        hide_index=True,
    )


def render_metrics_page(queries):
    st.header("Metrics")
    st.sidebar.title("Metrics Sections")

    section = st.sidebar.radio(
        "Select metrics section",
        [
            "Overview",
            "Cash Flow",
            "Category",
            "Account",
            "Portfolio",
            "Goods & Interest",
            "Pool Monthly Summary",
            "Data Health",
        ],
        index=0,
    )

    if section == "Overview":
        _render_overview_metrics(queries)
    elif section == "Cash Flow":
        _render_cash_flow_metrics(queries)
    elif section == "Category":
        _render_category_metrics(queries)
    elif section == "Account":
        _render_account_metrics(queries)
    elif section == "Portfolio":
        _render_portfolio_metrics(queries)
    elif section == "Goods & Interest":
        _render_goods_interest_metrics(queries)
    elif section == "Pool Monthly Summary":
        _render_pool_monthly_metrics(queries)
    elif section == "Data Health":
        _render_data_health_metrics(queries)
