import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import numpy as np
import pandas as pd
import streamlit as st


def _pyplot_spending_chart(queries, top_n=10, start_date=None, end_date=None):
    """Spending distribution by category."""

    categories = queries.get_spending_by_category(
        start_date=start_date,
        end_date=end_date,
    )
    if not categories:
        st.warning("No spending data found.")
        return

    df = pd.DataFrame(
        categories,
        columns=["Category", "Count", "Amount", "Average"]
    )

    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["Average"] = pd.to_numeric(df["Average"], errors="coerce")
    df = df.dropna(subset=["Amount"])

    if df.empty:
        st.warning("No valid spending data found for the selected period.")
        return

    df = (
        df.sort_values("Amount", ascending=True)
          .tail(top_n)
    )

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(14,6)
    )

    colors = plt.cm.Set3(np.arange(len(df)))

    ax1.pie(
        df["Amount"].abs(),
        labels=df["Category"],
        autopct="%1.1f%%",
        colors=colors,
        startangle=90
    )

    ax1.set_title("Spending Distribution")

    ax2.barh(
        df["Category"],
        df["Amount"].abs(),
        color=colors
    )

    ax2.set_xlabel("Amount")

    plt.tight_layout()
    st.pyplot(fig)

    return df

def _pyplot_account_balance_chart(queries):
    """Display current balance for each account."""

    balances = queries.get_account_balances()

    if not balances:
        st.warning("No account data found.")
        return

    df = pd.DataFrame(
        balances,
        columns=["Account", "Balance", "Last Transaction"]
    )

    df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce")
    df = df.sort_values("Balance", ascending=False)

    fig, ax = plt.subplots(figsize=(10, 6))

    sns.barplot(
        data=df,
        x="Balance",
        y="Account",
        palette="viridis",
        ax=ax
    )

    ax.set_title("Account Balances")
    ax.set_xlabel("Balance")
    ax.set_ylabel("")

    ax.xaxis.set_major_formatter(
        mtick.StrMethodFormatter("€{x:,.0f}")
    )

    plt.tight_layout()
    st.pyplot(fig)

    return df

def _pyplot_income_expense_chart(queries):
    """Compare total income and total expenses."""

    income = queries.get_total_income()
    expenses = queries.get_total_expenses()

    df = pd.DataFrame(
        {
            "Type": ["Income", "Expenses"],
            "Amount": [income, abs(expenses)]
        }
    )

    fig, ax = plt.subplots(figsize=(6, 5))

    sns.barplot(
        data=df,
        x="Type",
        y="Amount",
        palette=["green", "red"],
        ax=ax
    )

    ax.set_title("Income vs Expenses")
    ax.set_ylabel("Amount")

    ax.yaxis.set_major_formatter(
        mtick.StrMethodFormatter("€{x:,.0f}")
    )

    plt.tight_layout()
    st.pyplot(fig)

    return df

def _pyplot_transaction_frequency_chart(queries):
    """Show transaction count per category."""

    data = queries.get_transaction_frequency()

    if not data:
        st.warning("No transaction data found.")
        return

    df = pd.DataFrame(
        data,
        columns=["Category", "Transactions"]
    )

    df = df.sort_values(
        "Transactions",
        ascending=False
    )

    fig, ax = plt.subplots(figsize=(12, 6))

    sns.barplot(
        data=df,
        x="Transactions",
        y="Category",
        palette="Blues_r",
        ax=ax
    )

    ax.set_title("Transaction Frequency")

    plt.tight_layout()
    st.pyplot(fig)

    return df

def _pyplot_average_transaction_chart(queries):
    """Average transaction amount by category."""

    averages = queries.get_average_transaction()

    if not averages:
        st.warning("No transaction data found.")
        return

    df = pd.DataFrame(
        averages,
        columns=[
            "Category",
            "Average Amount"
        ]
    )

    df = df.sort_values(
        "Average Amount",
        ascending=False
    )

    fig, ax = plt.subplots(figsize=(12, 6))

    sns.barplot(
        data=df,
        x="Average Amount",
        y="Category",
        palette="magma",
        ax=ax
    )

    ax.set_title("Average Transaction Amount")

    ax.xaxis.set_major_formatter(
        mtick.StrMethodFormatter("€{x:,.0f}")
    )

    plt.tight_layout()
    st.pyplot(fig)

    return df

def _pyplot_depreciation_chart(
    queries,
    selected_assets=None,
):
    """
    Plot the latest goods valuation snapshot (purchase vs. current value)
    for the goods/degradation pool.
    """

    valuations = queries.get_latest_goods_valuations()

    if not valuations:
        st.warning("No goods valuation data available.")
        return

    df = pd.DataFrame(
        valuations,
        columns=[
            "Asset",
            "Purchase Value",
            "Current Value",
            "Value Change",
        ],
    )

    if selected_assets:
        df = df[df["Asset"].isin(selected_assets)]

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(df))
    width = 0.35

    ax.bar(x - width / 2, df["Purchase Value"].astype(float), width, label="Purchase Value", color="#4C72B0")
    ax.bar(x + width / 2, df["Current Value"].astype(float), width, label="Current Value", color="#DD8452")

    ax.set_xticks(x)
    ax.set_xticklabels(df["Asset"], rotation=45, ha="right")

    ax.set_title("Goods Valuation (Purchase vs. Current)")

    ax.set_ylabel("Value")

    ax.yaxis.set_major_formatter(
        mtick.StrMethodFormatter("€{x:,.0f}")
    )

    ax.grid(True, alpha=0.3)

    ax.legend()

    plt.tight_layout()

    st.pyplot(fig)

    return df


def _pyplot_goods_value_history_chart(queries):
    """Plot total goods value over time across monthly imports."""

    history = queries.get_goods_value_history()

    if not history:
        st.warning("No goods valuation history available.")
        return

    df = pd.DataFrame(history, columns=["Date", "Total Value"])
    df["Date"] = pd.to_datetime(df["Date"])

    fig, ax = plt.subplots(figsize=(13, 6))

    sns.lineplot(data=df, x="Date", y="Total Value", linewidth=3, marker="o", ax=ax)

    ax.set_title("Goods Total Value Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Total Value")

    ax.yaxis.set_major_formatter(
        mtick.StrMethodFormatter("€{x:,.0f}")
    )

    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    st.pyplot(fig)

    return df


def _pyplot_stock_positions_chart(queries, top_n=15):
    """Show the latest stock/crypto depot positions by value."""

    positions = queries.get_latest_stock_positions()

    if not positions:
        st.warning("No stock position data available.")
        return

    if len(positions[0]) == 2:
        latest_snapshot = positions[-1][0]
        positions = queries.get_stock_positions_by_snapshot_date(latest_snapshot)
        if not positions:
            st.warning("No stock position data available for the latest snapshot.")
            return

    if len(positions[0]) == 7:
        df = pd.DataFrame(
            positions,
            columns=["Name", "Ticker", "Quantity", "Price", "Position Value", "Delta Value", "Delta Percent"],
        )
    else:
        df = pd.DataFrame(positions)
        df = df.iloc[:, [2, 3, 4, 6, 9, 7, 8]]
        df.columns = ["Name", "Ticker", "Quantity", "Price", "Position Value", "Delta Value", "Delta Percent"]

    df = df.sort_values("Position Value", ascending=True).tail(top_n)

    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ["#55A868" if v >= 0 else "#C44E52" for v in df["Delta Value"].astype(float)]

    ax.barh(df["Name"], df["Position Value"].astype(float), color="#4C72B0")

    ax.set_title("Latest Stock/Crypto Depot Positions")
    ax.set_xlabel("Position Value")

    ax.xaxis.set_major_formatter(
        mtick.StrMethodFormatter("€{x:,.0f}")
    )

    plt.tight_layout()
    st.pyplot(fig)

    return df


def _pyplot_stock_value_history_chart(queries):
    """Plot total depot value over time across monthly imports."""

    history = queries.get_stock_value_history()

    if not history:
        st.warning("No stock value history available.")
        return

    df = pd.DataFrame(history, columns=["Date", "Total Value"])
    df["Date"] = pd.to_datetime(df["Date"])

    fig, ax = plt.subplots(figsize=(13, 6))

    sns.lineplot(data=df, x="Date", y="Total Value", linewidth=3, marker="o", ax=ax)
    ax.fill_between(df["Date"], df["Total Value"].astype(float), alpha=0.2)

    ax.set_title("Depot Total Value Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Total Value")

    ax.yaxis.set_major_formatter(
        mtick.StrMethodFormatter("€{x:,.0f}")
    )

    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    st.pyplot(fig)

    return df


def _pyplot_interest_balance_chart(queries):
    """Show the latest Festgeld/interest account balances."""

    balances = queries.get_latest_interest_balances()

    if not balances:
        st.warning("No interest balance data available.")
        return

    df = pd.DataFrame(balances, columns=["Change ID", "Account", "Balance", "Previous Balance", "Delta"])

    fig, ax = plt.subplots(figsize=(10, 6))

    sns.barplot(data=df, x="Balance", y="Account", palette="crest", ax=ax)

    ax.set_title("Interest Account Balances")
    ax.set_xlabel("Balance")
    ax.set_ylabel("")

    ax.xaxis.set_major_formatter(
        mtick.StrMethodFormatter("€{x:,.0f}")
    )

    plt.tight_layout()
    st.pyplot(fig)

    return df


def _pyplot_interest_balance_history_chart(queries):
    """Plot total interest balance over time across monthly imports."""

    history = queries.get_interest_balance_history()

    if not history:
        st.warning("No interest balance history available.")
        return

    df = pd.DataFrame(history, columns=["Date", "Total Balance", "Total Delta"])
    df["Date"] = pd.to_datetime(df["Date"])

    fig, ax = plt.subplots(figsize=(13, 6))

    sns.lineplot(data=df, x="Date", y="Total Balance", linewidth=3, marker="o", ax=ax)

    ax.set_title("Interest Balance Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Total Balance")

    ax.yaxis.set_major_formatter(
        mtick.StrMethodFormatter("€{x:,.0f}")
    )

    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    st.pyplot(fig)

    return df


def _pyplot_balance_timeline_chart(
    queries,
    start_date=None,
    end_date=None,
):
    """Plot combined timeline for cash, stocks, goods, and interest pools."""

    timeline = queries.get_all_pools_timeline(
        start_date=start_date,
        end_date=end_date,
    )

    if not timeline:
        st.warning("No timeline data available.")
        return

    df = pd.DataFrame(
        timeline,
        columns=[
            "Date",
            "Cash",
            "Stocks",
            "Goods",
            "Interest",
        ],
    )

    df["Date"] = pd.to_datetime(df["Date"])

    melted = df.melt(
        id_vars=["Date"],
        value_vars=["Cash", "Stocks", "Goods", "Interest"],
        var_name="Pool",
        value_name="Value",
    )

    fig, ax = plt.subplots(figsize=(13, 6))

    sns.lineplot(
        data=melted,
        x="Date",
        y="Value",
        hue="Pool",
        marker="o",
        linewidth=2.5,
        ax=ax,
    )

    ax.set_title("All Pools Timeline")
    ax.set_xlabel("Date")
    ax.set_ylabel("Value")
    ax.set_ylim(bottom=0)

    ax.yaxis.set_major_formatter(
        mtick.StrMethodFormatter("€{x:,.0f}")
    )

    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    st.pyplot(fig)

    return df