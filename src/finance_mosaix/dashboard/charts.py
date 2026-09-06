import altair as alt
import pandas as pd
import streamlit as st


def timeline_line_chart(
    queries,
    start_date=None,
    end_date=None,
    scale_type: str = "Linear",
    show_subheader: bool = True,
    selected_pools: list[str] | None = None,
):
    """Render a Streamlit native timeline chart for all pools or a single pool."""

    timeline = queries.get_all_pools_timeline(
        start_date=start_date,
        end_date=end_date,
    )

    if not timeline:
        st.warning("No timeline data available.")
        return None

    df = pd.DataFrame(
        timeline,
        columns=["Date", "Cash", "Stocks", "Goods", "Interest"],
    )
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    for col in ["Cash", "Stocks", "Goods", "Interest"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["Total"] = df[["Cash", "Stocks", "Goods", "Interest"]].sum(axis=1)
    df_long = df.melt(
        id_vars=["Date"],
        value_vars=["Cash", "Stocks", "Goods", "Interest", "Total"],
        var_name="Pool",
        value_name="Value",
    )

    selected_pools = selected_pools or ["Cash", "Stocks", "Goods", "Interest"]
    valid_pools = ["Cash", "Stocks", "Goods", "Interest"]
    active_pools = [pool for pool in valid_pools if pool in selected_pools]

    if active_pools and len(active_pools) < len(valid_pools):
        df_long = df_long[df_long["Pool"].isin(active_pools)]
        chart_title = f"Timeline — {', '.join(active_pools)}"
        subtitle = f"Showing timeline for selected pool(s): {', '.join(active_pools)}."
    else:
        chart_title = "Timeline"
        subtitle = "**Total combined value is shown as the `Total` line.**"

    if show_subheader:
        st.subheader(chart_title)
        st.markdown(subtitle)

    if scale_type not in {"Linear", "Logarithmic"}:
        scale_type = "Linear"

    if scale_type == "Logarithmic" and (df_long["Value"] <= 0).any():
        st.warning(
            "Logarithmic scale requires all timeline values to be positive. "
            "Showing the chart on a linear scale instead."
        )
        scale_type = "Linear"

    chart = alt.Chart(df_long).mark_line(point=True).encode(
        x=alt.X("Date:T", title="Date"),
        y=alt.Y(
            "Value:Q",
            title="Value",
            scale=alt.Scale(type="log" if scale_type == "Logarithmic" else "linear"),
        ),
        color=alt.Color("Pool:N", title="Pool"),
        tooltip=[
            alt.Tooltip("Date:T", title="Date"),
            alt.Tooltip("Pool:N", title="Pool"),
            alt.Tooltip("Value:Q", title="Value", format=",.2f"),
        ],
        size=alt.condition(
            alt.datum.Pool == "Total",
            alt.value(4),
            alt.value(2),
        ),
        strokeDash=alt.condition(
            alt.datum.Pool == "Total",
            alt.value([1, 0]),
            alt.value([5, 5]),
        ),
    ).properties(
        width="container",
        height=450,
    ).interactive()

    st.altair_chart(chart, width="stretch")

    return df


def latest_timeline_distribution_pie(
    queries,
    start_date=None,
    end_date=None,
    show_subheader: bool = True,
):
    """Render a pie chart showing the latest timeline values by pool."""

    timeline = queries.get_all_pools_timeline(
        start_date=start_date,
        end_date=end_date,
    )

    if not timeline:
        st.warning("No timeline data available for the latest distribution chart.")
        return None

    df = pd.DataFrame(
        timeline,
        columns=["Date", "Cash", "Stocks", "Goods", "Interest"],
    )
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    for col in ["Cash", "Stocks", "Goods", "Interest"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    latest_row = df.iloc[-1]
    latest_df = pd.DataFrame(
        {
            "Pool": ["Cash", "Stocks", "Goods", "Interest"],
            "Value": [
                latest_row["Cash"],
                latest_row["Stocks"],
                latest_row["Goods"],
                latest_row["Interest"],
            ],
        }
    )
    latest_df["Value"] = latest_df["Value"].abs()
    latest_df = latest_df[latest_df["Value"] > 0]

    if latest_df.empty:
        st.warning("No latest timeline values available to display.")
        return None

    if show_subheader:
        st.subheader(f"Latest Asset Distribution ({latest_row['Date'].date()})")
    st.metric("Latest Total Value", f"€{latest_df['Value'].sum():,.2f}")

    chart = alt.Chart(latest_df).mark_arc(innerRadius=60).encode(
        theta=alt.Theta("Value:Q", title="Value"),
        color=alt.Color("Pool:N", title="Pool"),
        tooltip=[
            alt.Tooltip("Pool:N", title="Pool"),
            alt.Tooltip("Value:Q", title="Value", format=",.2f"),
        ],
    ).properties(
        width="container",
        height=360,
    )

    st.altair_chart(chart, width="stretch")

    return latest_df


def _split_category_hierarchy(category_name):
    if category_name is None:
        return "Uncategorized", None

    category_name = str(category_name).strip()
    if not category_name:
        return "Uncategorized", None

    if "/" in category_name:
        main, sub = category_name.split("/", 1)
        return main.strip() or "Uncategorized", sub.strip() or "Uncategorized"

    return category_name, None


def asset_allocation_trend_chart(
    queries,
    start_date=None,
    end_date=None,
    selected_pools: list[str] | None = None,
):
    """Render the asset allocation trend chart by pool over time."""

    timeline = queries.get_all_pools_timeline(
        start_date=start_date,
        end_date=end_date,
    )

    if not timeline:
        st.warning("No timeline data available for asset allocation trend.")
        return None

    df = pd.DataFrame(
        timeline,
        columns=["Date", "Cash", "Stocks", "Goods", "Interest"],
    )
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
    for col in ["Cash", "Stocks", "Goods", "Interest"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df_long = df.melt(
        id_vars=["Date"],
        value_vars=["Cash", "Stocks", "Goods", "Interest"],
        var_name="Pool",
        value_name="Value",
    )

    selected_pools = selected_pools or ["Cash", "Stocks", "Goods", "Interest"]
    valid_pools = ["Cash", "Stocks", "Goods", "Interest"]
    active_pools = [pool for pool in valid_pools if pool in selected_pools]

    if active_pools and len(active_pools) < len(valid_pools):
        df_long = df_long[df_long["Pool"].isin(active_pools)]
        title = f"Asset Allocation Trend — {', '.join(active_pools)}"
        description = (
            f"This chart shows the selected pool trend for {', '.join(active_pools)} over time."
        )
    else:
        title = "Asset Allocation Trend"
        description = (
            "This chart shows how the portfolio allocation across Cash, Stocks, Goods, and Interest changes over time."
        )

    st.subheader(title)
    st.markdown(description)

    chart = alt.Chart(df_long).mark_area(opacity=0.72).encode(
        x=alt.X("Date:T", title="Date"),
        y=alt.Y(
            "Value:Q",
            title="Allocation",
            stack="normalize",
            axis=alt.Axis(format="%"),
        ),
        color=alt.Color("Pool:N", title="Pool"),
        tooltip=[
            alt.Tooltip("Date:T", title="Date"),
            alt.Tooltip("Pool:N", title="Pool"),
            alt.Tooltip("Value:Q", title="Value", format=",.2f"),
        ],
    ).properties(width="container", height=450).interactive()

    st.altair_chart(chart, width="stretch")
    return df


def monthly_cashflow_trend_chart(
    queries,
    start_date=None,
    end_date=None,
):
    """Render the monthly cash flow trend chart for income and expenses."""

    if start_date is None or end_date is None:
        available_start, available_end = queries.get_database_date_range()
        start_date = start_date or available_start
        end_date = end_date or available_end

    if start_date is None or end_date is None:
        st.warning("No date range available for cash flow trend.")
        return None

    rows = queries.conn.execute(
        """
        SELECT
            DATE_TRUNC('month', transaction_date)::DATE AS month,
            SUM(CASE WHEN c.category_type = 'income' THEN t.amount ELSE 0 END) AS income,
            SUM(CASE WHEN c.category_type = 'expense' THEN ABS(t.amount) ELSE 0 END) AS expense
        FROM cash_transactions t
        JOIN categories c ON t.category_id = c.category_id
        WHERE t.transaction_date BETWEEN ? AND ?
        GROUP BY month
        ORDER BY month
        """,
        [start_date, end_date],
    ).fetchall()

    if not rows:
        st.warning("No monthly cash flow data available for the selected date range.")
        return None

    df = pd.DataFrame(rows, columns=["Month", "Income", "Expense"])
    df["Month"] = pd.to_datetime(df["Month"])
    df = df.sort_values("Month")
    df_long = df.melt(
        id_vars=["Month"],
        value_vars=["Income", "Expense"],
        var_name="Type",
        value_name="Amount",
    )

    st.subheader("Cash Flow Trend")
    st.markdown(
        "Monthly income and expense trend across the selected date range."
    )

    chart = alt.Chart(df_long).mark_line(point=True).encode(
        x=alt.X("Month:T", title="Month"),
        y=alt.Y("Amount:Q", title="Amount"),
        color=alt.Color("Type:N", title="Flow"),
        tooltip=[
            alt.Tooltip("Month:T", title="Month"),
            alt.Tooltip("Type:N", title="Type"),
            alt.Tooltip("Amount:Q", title="Amount", format=",.2f"),
        ],
    ).properties(width="container", height=450).interactive()

    total_income = df["Income"].sum()
    total_expense = df["Expense"].sum()
    net = total_income - total_expense
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"€{total_income:,.2f}")
    col2.metric("Total Expenses", f"€{total_expense:,.2f}")
    col3.metric("Net Flow", f"€{net:,.2f}")

    st.altair_chart(chart, width="stretch")
    return df


def category_drilldown_chart(
    queries,
    start_date=None,
    end_date=None,
    top_n=12,
):
    """Render a drill-down view of spending by main category and subcategory."""

    categories = queries.get_spending_by_category(
        start_date=start_date,
        end_date=end_date,
    )
    if not categories:
        st.warning("No spending data found for the selected period.")
        return None

    df = pd.DataFrame(
        categories,
        columns=["Category", "Count", "Amount", "Average"],
    )
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").abs().fillna(0.0)
    if df.empty:
        st.warning("No valid spending data found for the selected period.")
        return None

    df[["Main Category", "Sub Category"]] = df["Category"].apply(
        lambda value: pd.Series(_split_category_hierarchy(value))
    )
    df["Sub Category"] = df["Sub Category"].fillna("Other")

    main_df = (
        df.groupby("Main Category", as_index=False)["Amount"].sum()
        .sort_values("Amount", ascending=False)
        .head(top_n)
    )

    selected_main = st.selectbox(
        "Main category",
        main_df["Main Category"].tolist(),
        index=0,
        help="Choose a main category to inspect its subcategory spending.",
    )

    sub_df = (
        df[df["Main Category"] == selected_main]
        .groupby("Sub Category", as_index=False)["Amount"].sum()
        .sort_values("Amount", ascending=False)
        .head(top_n)
    )

    st.subheader("Category Spending Drill-down")
    st.markdown(
        "Explore spending by top-level category and inspect its subcategory breakdown."
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("**Top main categories**")
        chart = alt.Chart(main_df).mark_bar().encode(
            x=alt.X("Amount:Q", title="Total Spend"),
            y=alt.Y("Main Category:N", sort="-x", title="Main Category"),
            color=alt.Color("Amount:Q", scale=alt.Scale(scheme="oranges"), legend=None),
            tooltip=[
                alt.Tooltip("Main Category:N", title="Main Category"),
                alt.Tooltip("Amount:Q", title="Amount", format=",.2f"),
            ],
        ).properties(width="container", height=420)
        st.altair_chart(chart, use_container_width=True)

    with col2:
        st.markdown(f"**Subcategories for {selected_main}**")
        chart = alt.Chart(sub_df).mark_bar().encode(
            x=alt.X("Amount:Q", title="Spend"),
            y=alt.Y("Sub Category:N", sort="-x", title="Subcategory"),
            color=alt.Color("Amount:Q", scale=alt.Scale(scheme="blues"), legend=None),
            tooltip=[
                alt.Tooltip("Sub Category:N", title="Subcategory"),
                alt.Tooltip("Amount:Q", title="Amount", format=",.2f"),
            ],
        ).properties(width="container", height=420)
        st.altair_chart(chart, use_container_width=True)

    return df


def account_balance_history_chart(
    queries,
    start_date=None,
    end_date=None,
    selected_pools: list[str] | None = None,
    max_accounts=5,
):
    """Render historical account balance trends for selected accounts."""

    selected_pools = selected_pools or ["Cash", "Interest"]
    show_cash = "Cash" in selected_pools
    show_interest = "Interest" in selected_pools

    all_entries = []
    if show_cash:
        cash_entries = queries.account_balance.get_account_balance_entries(
            start_date=start_date,
            end_date=end_date,
        )
        all_entries.extend(
            [
                {
                    "Balance ID": row[0],
                    "Date": row[1],
                    "Account": row[2],
                    "Balance": row[3],
                    "Previous Balance": row[4],
                    "Delta": row[5],
                    "Entry Type": row[6],
                    "Source Sheet": row[7],
                }
                for row in cash_entries
            ]
        )

    if show_interest:
        interest_entries = queries.interest.get_interest_balance_changes(
            start_date=start_date,
            end_date=end_date,
        )
        all_entries.extend(
            [
                {
                    "Balance ID": row[0],
                    "Date": row[1],
                    "Account": row[2],
                    "Balance": row[3],
                    "Previous Balance": row[4],
                    "Delta": row[5],
                    "Entry Type": "interest",
                    "Source Sheet": row[6],
                }
                for row in interest_entries
            ]
        )

    if not all_entries:
        st.warning("No account balance history available for the selected date range and pools.")
        return None

    df = pd.DataFrame(
        all_entries,
        columns=[
            "Balance ID",
            "Date",
            "Account",
            "Balance",
            "Previous Balance",
            "Delta",
            "Entry Type",
            "Source Sheet",
        ],
    )
    df["Date"] = pd.to_datetime(df["Date"])
    df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce").fillna(0.0)

    account_names = df["Account"].dropna().unique().tolist()
    selected_accounts = st.multiselect(
        "Accounts",
        sorted(account_names),
        default=sorted(account_names),
        help="Select accounts to compare historical balances.",
    )

    if not selected_accounts:
        st.warning("Select at least one account to display history.")
        return None

    df = df[df["Account"].isin(selected_accounts)]
    if df.empty:
        st.warning("No balance history available for the selected accounts.")
        return None

    st.subheader("Account Balance History")
    st.markdown(
        "Historical balance trends for selected accounts over the chosen date range."
    )

    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("Date:T", title="Date"),
        y=alt.Y("Balance:Q", title="Balance"),
        color=alt.Color("Account:N", title="Account"),
        tooltip=[
            alt.Tooltip("Date:T", title="Date"),
            alt.Tooltip("Account:N", title="Account"),
            alt.Tooltip("Balance:Q", title="Balance", format=",.2f"),
        ],
    ).properties(width="container", height=450).interactive()

    total_accounts = len(selected_accounts)
    latest_snapshot = df.sort_values(["Date"]).drop_duplicates("Account", keep="last")
    total_latest = latest_snapshot["Balance"].sum()
    st.metric("Accounts Tracked", total_accounts)
    st.metric("Latest Combined Balance", f"€{total_latest:,.2f}")
    st.altair_chart(chart, width="stretch")
    return df


def stock_portfolio_performance_chart(
    queries,
):
    """Render stock portfolio performance over time."""

    history = queries.get_stock_value_history()
    if not history:
        st.warning("No stock portfolio history available.")
        return None

    df = pd.DataFrame(history, columns=["Date", "Total Value"])
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    st.subheader("Stock Portfolio Performance")
    st.markdown(
        "Track the total stock portfolio value across available snapshots."
    )

    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("Date:T", title="Date"),
        y=alt.Y("Total Value:Q", title="Portfolio Value"),
        tooltip=[
            alt.Tooltip("Date:T", title="Date"),
            alt.Tooltip("Total Value:Q", title="Total Value", format=",.2f"),
        ],
    ).properties(width="container", height=450).interactive()

    st.altair_chart(chart, width="stretch")
    latest_value = df["Total Value"].iloc[-1]
    change = df["Total Value"].diff().iloc[-1] if len(df) > 1 else 0.0
    st.metric("Latest Portfolio Value", f"€{latest_value:,.2f}", delta=f"€{change:,.2f}")
    return df


def goods_value_history_chart(
    queries,
):
    """Render goods valuation change over time."""

    item_names = queries.goods.get_goods_item_names()
    selection = ["All items"] + item_names
    selected_item = st.selectbox(
        "Goods item",
        selection,
        index=0,
        help="Select a specific goods item or view the aggregate goods valuation trend.",
    )

    selected_item_name = None if selected_item == "All items" else selected_item
    history = queries.get_goods_value_history(item_name=selected_item_name)
    if not history:
        st.warning("No goods valuation history available.")
        return None

    df = pd.DataFrame(history, columns=["Date", "Total Value"])
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    title = "Goods Valuation Change Over Time"
    if selected_item_name is not None:
        title = f"Goods Valuation Change Over Time — {selected_item_name}"

    st.subheader(title)
    st.markdown(
        "This chart tracks how goods current value evolved over time."
    )

    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("Date:T", title="Date"),
        y=alt.Y("Total Value:Q", title="Value"),
        tooltip=[
            alt.Tooltip("Date:T", title="Date"),
            alt.Tooltip("Total Value:Q", title="Value", format=",.2f"),
        ],
    ).properties(width="container", height=450).interactive()

    st.altair_chart(chart, width="stretch")
    latest_value = df["Total Value"].iloc[-1]
    st.metric("Latest Goods Value", f"€{latest_value:,.2f}")
    return df


def interest_growth_chart(
    queries,
):
    """Render interest growth over time."""

    account_names = queries.interest.get_interest_account_names()
    selection = ["All accounts"] + account_names
    selected_account = st.selectbox(
        "Interest account",
        selection,
        index=0,
        help="Select an interest account or view the aggregate interest balance trend.",
    )

    selected_account_name = None if selected_account == "All accounts" else selected_account
    history = queries.get_interest_balance_history(account_name=selected_account_name)
    if not history:
        st.warning("No interest balance history available.")
        return None

    df = pd.DataFrame(history, columns=["Date", "Total Balance", "Total Delta"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["Total Balance"] = pd.to_numeric(df["Total Balance"], errors="coerce").fillna(0.0)
    df = df.sort_values("Date")

    title = "Interest Growth Over Time"
    if selected_account_name is not None:
        title = f"Interest Growth Over Time — {selected_account_name}"

    st.subheader(title)
    st.markdown(
        "Interest balance trend over time for the selected account or aggregate account set."
    )

    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("Date:T", title="Date"),
        y=alt.Y("Total Balance:Q", title="Interest Balance"),
        tooltip=[
            alt.Tooltip("Date:T", title="Date"),
            alt.Tooltip("Total Balance:Q", title="Balance", format=",.2f"),
            alt.Tooltip("Total Delta:Q", title="Delta", format=",.2f"),
        ],
    ).properties(width="container", height=450).interactive()

    st.altair_chart(chart, width="stretch")
    latest_balance = df["Total Balance"].iloc[-1]
    st.metric("Latest Interest Balance", f"€{latest_balance:,.2f}")
    return df


def spending_chart(
    queries,
    top_n=10,
    start_date=None,
    end_date=None,
):
    """Render spending as native Streamlit charts for category totals."""

    categories = queries.get_spending_by_category(
        start_date=start_date,
        end_date=end_date,
    )

    if not categories:
        st.warning("No spending data found.")
        return None

    df = pd.DataFrame(
        categories,
        columns=["Category", "Count", "Amount", "Average"],
    )

    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").abs()
    df["Average"] = pd.to_numeric(df["Average"], errors="coerce").abs()
    df = df.dropna(subset=["Amount"])

    if df.empty:
        st.warning("No valid spending data found for the selected period.")
        return None

    df = df.sort_values("Amount", ascending=False).head(top_n)
    df = df.reset_index(drop=True)

    total_spending = df["Amount"].sum()
    average_per_category = df["Amount"].mean()
    top_category = df.iloc[0]["Category"] if not df.empty else "N/A"

    st.subheader("Spending")
    st.metric("Total Spending", f"€{total_spending:,.2f}")
    st.metric("Average Category Spend", f"€{average_per_category:,.2f}")
    st.metric("Top Category", top_category)

    chart_df = df.set_index("Category")[ ["Amount", "Average"] ]
    st.bar_chart(
        chart_df,
        width="stretch"
    )

    return df


def income_vs_expense_chart(
    queries,
    start_date=None,
    end_date=None,
):
    """Render a native Income vs Expenses chart with metrics."""

    net_income = queries.get_net_income(start_date=start_date, end_date=end_date)
    if not net_income:
        income = queries.get_total_income() or 0.0
        expenses = abs(queries.get_total_expenses() or 0.0)
        data = [("income", income), ("expense", expenses)]
    else:
        data = []
        for entry_type, total in net_income:
            value = float(total or 0)
            if entry_type.lower() == "expense":
                value = abs(value)
            data.append((entry_type.capitalize(), value))

    df = pd.DataFrame(data, columns=["Type", "Amount"]).sort_values("Amount", ascending=False)
    if df.empty:
        st.warning("No income/expense data available.")
        return None

    total_income = df.loc[df["Type"].str.lower() == "income", "Amount"].sum()
    total_expense = df.loc[df["Type"].str.lower() == "expense", "Amount"].sum()
    net = total_income - total_expense

    st.subheader("Income vs Expenses")
    col1, col2, col3 = st.columns(3)
    col1.metric("Income", f"€{total_income:,.2f}")
    col2.metric("Expenses", f"€{total_expense:,.2f}")
    col3.metric("Net", f"€{net:,.2f}")

    st.bar_chart(df.set_index("Type"), width="stretch")
    return df


def transaction_frequency_chart(
    queries,
    top_n=20,
):
    """Render a native transaction frequency chart using horizontal bars."""

    data = queries.get_transaction_frequency()
    if not data:
        st.warning("No transaction frequency data found.")
        return None

    df = pd.DataFrame(data, columns=["Category", "Transactions"])
    df["Transactions"] = pd.to_numeric(df["Transactions"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("Transactions", ascending=True).tail(top_n)

    if df.empty:
        st.warning("No valid transaction frequency data found.")
        return None

    st.subheader("Transaction Frequency")
    st.markdown(
        "The chart below shows the number of transactions per category, ordered by highest frequency."
    )

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Transactions:Q", title="Transactions"),
        y=alt.Y("Category:N", sort="-x", title="Category"),
        tooltip=[
            alt.Tooltip("Category:N", title="Category"),
            alt.Tooltip("Transactions:Q", title="Transactions"),
        ],
    ).properties(width="container", height=450)

    st.altair_chart(chart, use_container_width=True)
    return df


def average_transaction_chart(
    queries,
    top_n=20,
):
    """Render a native average transaction chart with ranked categories."""

    averages = queries.get_average_transaction()
    if not averages:
        st.warning("No average transaction data found.")
        return None

    df = pd.DataFrame(averages, columns=["Category", "Average Amount"])
    df["Average Amount"] = pd.to_numeric(df["Average Amount"], errors="coerce").fillna(0.0)
    df = df.sort_values("Average Amount", ascending=False).head(top_n)

    if df.empty:
        st.warning("No valid average transaction data found.")
        return None

    overall_avg = df["Average Amount"].mean() if not df.empty else 0.0
    top_category = df.iloc[0]["Category"] if not df.empty else "N/A"

    st.subheader("Average Transaction Amount")
    col1, col2 = st.columns([1, 2])
    col1.metric("Average Amount", f"€{overall_avg:,.2f}")
    col2.metric("Top Category", top_category)

    st.area_chart(df.set_index("Category"), width="stretch")
    return df


def balances_chart(
    queries,
    start_date=None,
    end_date=None,
    selected_pools: list[str] | None = None,
    hide_zero_balances: bool = False,
):
    """Render a Streamlit native balances chart and tracking metrics."""

    selected_pools = selected_pools or ["Cash", "Interest"]
    show_cash = "Cash" in selected_pools
    show_interest = "Interest" in selected_pools

    if show_cash and not show_interest:
        balances = queries.get_account_balances()
        if not balances:
            st.warning("No account balance data available.")
            return None

        df = pd.DataFrame(
            balances,
            columns=["Account", "Balance", "Last Transaction"],
        )
        df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce").fillna(0.0)
        df = df.sort_values("Balance", ascending=False)

        history = queries.account_balance.get_account_balance_history(entry_type="calculated")
        if not history:
            history = queries.account_balance.get_account_balance_history()

        title = "Account Balances"
        subtitle = "Latest cash account balances for the selected filters."
        total_label = "Total Balance"
    elif show_interest and not show_cash:
        balances = queries.get_latest_interest_balances()
        if not balances:
            st.warning("No interest balance data available.")
            return None

        df = pd.DataFrame(
            balances,
            columns=["Change ID", "Account", "Balance", "Previous Balance", "Delta"],
        )
        df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce").fillna(0.0)
        df = df.sort_values("Balance", ascending=False)

        history = queries.get_interest_balance_history()
        title = "Balance with Delta"
        subtitle = "Latest interest account balances for the selected filters."
        total_label = "Total Interest Balance"
    else:
        cash_balances = queries.get_account_balances()
        interest_balances = queries.get_latest_interest_balances()

        cash_df = (
            pd.DataFrame(cash_balances, columns=["Account", "Balance", "Last Transaction"]).assign(Type="Cash")
            if cash_balances
            else pd.DataFrame(columns=["Account", "Balance", "Last Transaction", "Type"])
        )
        interest_df = (
            pd.DataFrame(
                interest_balances,
                columns=["Change ID", "Account", "Balance", "Previous Balance", "Delta"],
            ).assign(Type="Interest")
            if interest_balances
            else pd.DataFrame(columns=["Account", "Balance", "Type"])
        )

        if cash_df.empty and interest_df.empty:
            st.warning("No cash or interest balance data available.")
            return None

        if not cash_df.empty:
            cash_df["Balance"] = pd.to_numeric(cash_df["Balance"], errors="coerce").fillna(0.0)
            cash_df = cash_df[["Account", "Balance", "Type"]]
        if not interest_df.empty:
            interest_df["Balance"] = pd.to_numeric(interest_df["Balance"], errors="coerce").fillna(0.0)
            interest_df = interest_df[["Account", "Balance", "Type"]]

        df = pd.concat([cash_df, interest_df], ignore_index=True)
        df = df.sort_values("Balance", ascending=False)

        history = queries.account_balance.get_account_balance_history(entry_type="calculated")
        if not history:
            history = queries.account_balance.get_account_balance_history()

        title = "Cash & Interest Balances"
        subtitle = "Latest cash and interest balances for the selected filters."
        total_label = "Total Balance"

    if hide_zero_balances:
        df = df[df["Balance"] != 0.0]
        if df.empty:
            st.warning("No balances available after filtering out zero values.")
            return None

    total_balance = df["Balance"].sum()
    change_label = "Tracking change"
    tracking_delta = None
    snapshot_date = None

    if history:
        history_df = pd.DataFrame(
            history,
            columns=["Date", "Total Balance", "Total Delta"],
        )
        history_df["Date"] = pd.to_datetime(history_df["Date"])
        history_df["Total Balance"] = pd.to_numeric(history_df["Total Balance"], errors="coerce").fillna(0.0)
        history_df["Total Delta"] = pd.to_numeric(history_df["Total Delta"], errors="coerce")
        history_df = history_df.sort_values("Date")

        latest = history_df.iloc[-1]
        snapshot_date = latest["Date"].date()
        if pd.notna(latest["Total Delta"]):
            tracking_delta = float(latest["Total Delta"])
        elif len(history_df) >= 2:
            previous = history_df.iloc[-2]
            tracking_delta = float(latest["Total Balance"] - previous["Total Balance"])

    col1, col2, col3 = st.columns([1, 1, 1])
    col1.metric(total_label, f"€{total_balance:,.2f}")

    if tracking_delta is not None:
        col2.metric(
            change_label,
            f"€{tracking_delta:,.2f}",
            delta=f"€{tracking_delta:,.2f}",
        )
    else:
        col2.metric(change_label, "N/A")

    if snapshot_date is not None:
        col3.metric("Latest Snapshot", snapshot_date.strftime("%Y-%m-%d"))
    else:
        col3.metric("Latest Snapshot", "Unknown")

    st.subheader(title)
    if "Type" in df.columns and df["Type"].nunique() > 1:
        chart_df = df.set_index(["Account", "Type"])["Balance"].unstack(fill_value=0)
        st.bar_chart(chart_df, width="stretch")
    else:
        st.bar_chart(df.set_index("Account")["Balance"], width="stretch")

    return df


def stock_positions_chart(
    queries,
    top_n=20,
):
    """Render a native stock positions chart for the latest snapshot."""

    positions = queries.get_latest_stock_positions()
    if not positions:
        st.warning("No stock position data available.")
        return None

    if len(positions[0]) == 2:
        latest_snapshot = positions[-1][0]
        positions = queries.get_stock_positions_by_snapshot_date(latest_snapshot)
        if not positions:
            st.warning("No stock position data available for the latest snapshot.")
            return None

    if len(positions[0]) == 7:
        df = pd.DataFrame(
            positions,
            columns=[
                "Name",
                "Ticker",
                "Quantity",
                "Price",
                "Position Value",
                "Delta Value",
                "Delta Percent",
            ],
        )
    else:
        df = pd.DataFrame(positions)

    for col in ["Quantity", "Price", "Position Value", "Delta Value", "Delta Percent"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df = df.sort_values("Position Value", ascending=False).head(top_n)
    if df.empty:
        st.warning("No valid stock position data available.")
        return None

    total_value = df["Position Value"].sum()
    st.subheader("Stock Positions")
    st.metric("Tracked Positions", len(df))
    st.metric("Total Value", f"€{total_value:,.2f}")

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Position Value:Q", title="Position Value"),
        y=alt.Y("Name:N", sort="-x", title="Stock"),
        color=alt.Color("Delta Value:Q", title="Delta Value", scale=alt.Scale(scheme="teals")),
        tooltip=[
            alt.Tooltip("Name:N", title="Name"),
            alt.Tooltip("Ticker:N", title="Ticker"),
            alt.Tooltip("Position Value:Q", title="Position Value", format=",.2f"),
            alt.Tooltip("Quantity:Q", title="Quantity"),
            alt.Tooltip("Price:Q", title="Price", format=",.2f"),
            alt.Tooltip("Delta Percent:Q", title="Delta %", format=".2f"),
        ],
    ).properties(width="container", height=480)

    st.altair_chart(chart, use_container_width=True)
    return df


def goods_valuation_chart(
    queries,
    top_n=20,
):
    """Render a native goods valuation chart for the latest snapshot."""

    valuations = queries.get_latest_goods_valuations()
    if not valuations:
        st.warning("No goods valuation data available.")
        return None

    df = pd.DataFrame(
        valuations,
        columns=["Item", "Purchase Value", "Current Value", "Value Change"],
    )
    for col in ["Purchase Value", "Current Value", "Value Change"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df = df.sort_values("Current Value", ascending=False).head(top_n)
    if df.empty:
        st.warning("No valid goods valuation data available.")
        return None

    total_current_value = df["Current Value"].sum()
    total_change = df["Value Change"].sum()

    st.subheader("Goods Valuation")
    st.metric("Tracked Items", len(df))
    st.metric("Total Current Value", f"€{total_current_value:,.2f}")
    st.metric("Total Change", f"€{total_change:,.2f}")

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Current Value:Q", title="Current Value"),
        y=alt.Y("Item:N", sort="-x", title="Item"),
        color=alt.Color("Value Change:Q", title="Value Change", scale=alt.Scale(scheme="goldorange")),
        tooltip=[
            alt.Tooltip("Item:N", title="Item"),
            alt.Tooltip("Purchase Value:Q", title="Purchase Value", format=",.2f"),
            alt.Tooltip("Current Value:Q", title="Current Value", format=",.2f"),
            alt.Tooltip("Value Change:Q", title="Value Change", format=",.2f"),
        ],
    ).properties(width="container", height=480)

    st.altair_chart(chart, use_container_width=True)
    return df


def balance_delta_chart(
    queries,
    top_n=20,
    selected_pools: list[str] | None = None,
):
    """Render a native Balance with Delta chart for the latest snapshot."""

    selected_pools = selected_pools or ["Interest"]
    show_cash = "Cash" in selected_pools
    show_interest = "Interest" in selected_pools

    if show_cash and not show_interest:
        balances = queries.get_account_balances()
        if not balances:
            st.warning("No cash balance data available.")
            return None

        df = pd.DataFrame(balances, columns=["Account", "Balance", "Last Transaction"])
        df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce").fillna(0.0)
        df = df.sort_values("Balance", ascending=False).head(top_n)
        if df.empty:
            st.warning("No valid cash balance data available.")
            return None

        total_balance = df["Balance"].sum()
        st.subheader("Cash Balances")
        st.metric("Accounts Tracked", len(df))
        st.metric("Total Cash Balance", f"€{total_balance:,.2f}")

        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("Balance:Q", title="Balance"),
            y=alt.Y("Account:N", sort="-x", title="Account"),
            tooltip=[
                alt.Tooltip("Account:N", title="Account"),
                alt.Tooltip("Balance:Q", title="Balance", format=",.2f"),
            ],
        ).properties(width="container", height=480)

        st.altair_chart(chart, use_container_width=True)
        return df

    if show_interest:
        interest_balances = queries.get_latest_interest_balances()
    else:
        interest_balances = []

    cash_balances = queries.get_account_balances() if show_cash else []

    cash_df = (
        pd.DataFrame(cash_balances, columns=["Account", "Balance", "Last Transaction"]).assign(Type="Cash")
        if cash_balances
        else pd.DataFrame(columns=["Account", "Balance", "Last Transaction", "Type"])
    )
    interest_df = (
        pd.DataFrame(
            interest_balances,
            columns=["Change ID", "Account", "Balance", "Previous Balance", "Delta"],
        ).assign(Type="Interest")
        if interest_balances
        else pd.DataFrame(columns=["Account", "Balance", "Type"])
    )

    if cash_df.empty and interest_df.empty:
        st.warning("No selected balance data available.")
        return None

    if not cash_df.empty:
        cash_df["Balance"] = pd.to_numeric(cash_df["Balance"], errors="coerce").fillna(0.0)
        cash_df["Delta"] = 0.0
        cash_df = cash_df[["Account", "Balance", "Type", "Delta"]]
    if not interest_df.empty:
        interest_df["Balance"] = pd.to_numeric(interest_df["Balance"], errors="coerce").fillna(0.0)
        interest_df["Delta"] = pd.to_numeric(interest_df["Delta"], errors="coerce").fillna(0.0)
        interest_df = interest_df[["Account", "Balance", "Type", "Delta"]]

    df = pd.concat([cash_df, interest_df], ignore_index=True)
    if "Delta" not in df.columns:
        df["Delta"] = 0.0
    df["Delta"] = pd.to_numeric(df["Delta"], errors="coerce").fillna(0.0)
    df = df.sort_values("Balance", ascending=False).head(top_n)
    if df.empty:
        st.warning("No valid balance data available.")
        return None

    total_balance = df["Balance"].sum()
    total_delta = df["Delta"].sum()
    total_interest_delta = df.loc[df["Type"] == "Interest", "Delta"].sum()

    title = "Balance with Delta"
    if show_cash and show_interest:
        title = "Cash & Interest Balances"
    elif show_cash:
        title = "Cash Balances"

    st.subheader(title)
    st.metric("Accounts Tracked", len(df))
    st.metric("Total Balance", f"€{total_balance:,.2f}")
    if show_interest and not df[df["Type"] == "Interest"].empty:
        st.metric("Total Interest Delta", f"€{total_interest_delta:,.2f}")

    color_encoding = alt.Color(
        "Delta:Q",
        title="Delta",
        scale=alt.Scale(scheme="purpleorange"),
        legend=alt.Legend(title="Delta"),
    ) if show_interest else alt.value("steelblue")

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Balance:Q", title="Balance"),
        y=alt.Y("Account:N", sort="-x", title="Account"),
        color=color_encoding,
        tooltip=[
            alt.Tooltip("Account:N", title="Account"),
            alt.Tooltip("Type:N", title="Type"),
            alt.Tooltip("Balance:Q", title="Balance", format=",.2f"),
            alt.Tooltip("Delta:Q", title="Delta", format=",.2f"),
        ],
    ).properties(width="container", height=480)

    st.altair_chart(chart, use_container_width=True)
    return df
