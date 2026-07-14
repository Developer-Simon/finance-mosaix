import calendar
import sys
from datetime import date, timedelta
from importlib import import_module
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import dashboard.charts_pyplot as charts_pyplot
from dashboard.charts import (
    timeline_line_chart,
    latest_timeline_distribution_pie,
    spending_chart,
    balances_chart,
    income_vs_expense_chart,
    transaction_frequency_chart,
    average_transaction_chart,
    asset_allocation_trend_chart,
    monthly_cashflow_trend_chart,
    category_drilldown_chart,
    account_balance_history_chart,
    stock_portfolio_performance_chart,
    goods_value_history_chart,
    interest_growth_chart,
    stock_positions_chart,
    goods_valuation_chart,
    balance_delta_chart,
)
from dashboard.metrics import render_metrics_page
from dashboard.data import *
from src.db_schema import init_database
from src.query_finance import FinanceQueries

import_module("dashboard.import")
render_import_view = import_module("dashboard.import").render_import_view

from dashboard.data_creator import render_data_creator_view
from dashboard.data_editor import render_data_editor_view
from dashboard.data_organizer import render_data_organizer_view
from dashboard.settings import CHART_OPTIONS, render_settings_view, load_settings, save_settings

CHART_POOL_REQUIREMENTS = {
    "Timeline": {"Cash", "Stocks", "Goods", "Interest"},
    "Asset Allocation Trend": {"Cash", "Stocks", "Goods", "Interest"},
    "Spending": {"Cash"},
    "Balances": {"Cash", "Interest"},
    "Income vs Expenses": {"Cash"},
    "Transaction Frequency": {"Cash"},
    "Average Transaction": {"Cash"},
    "Cash Flow Trend": {"Cash"},
    "Category Drill-down": {"Cash"},
    "Account Balance History": {"Cash", "Interest"},
    "Stock Portfolio Performance": {"Stocks"},
    "Goods Valuation Change": {"Goods"},
    "Interest Growth": {"Interest"},
    "Stock Positions": {"Stocks"},
    "Goods Valuation": {"Goods"},
    "Balance with Delta": {"Cash", "Interest"},
}

st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="💰",
    layout="wide",
    menu_items={
        "About": "Finance Dashboard - Streamlit App for Personal Finance Database",
    }
)

db_path = str(ROOT_DIR / "finance_sample.duckdb")

@st.cache_resource(show_spinner=False)
def get_cached_queries(db_path: str):
    """Initialize the database once per Streamlit server session and return the query layer."""
    init_database(db_path)
    return FinanceQueries(db_path)

queries = get_cached_queries(db_path)
settings = load_settings()
application_mode = settings.get("dashboard", {}).get("application_mode", "Standard")
legacy_pyplots_enabled = settings.get("charts", {}).get("use_legacy_pyplots", False)
is_simple_mode = application_mode == "Simple"
is_expert_mode = application_mode == "Expert"

years = list(range(date.today().year - 10, date.today().year + 1))
month_names = list(calendar.month_name)[1:]

def _get_date_range():
    filter_options = ["Full database", "Month range", "Exact dates"]
    default_filter = settings.get("charts", {}).get("default_filter_mode", "Full database")
    filter_mode = st.sidebar.radio(
        "Filter by",
        filter_options,
        index=filter_options.index(default_filter) if default_filter in filter_options else 0,
        help="Choose whether to filter by exact dates, by month range, or across the full database.",
    )

    if filter_mode == "Exact dates":
        start_date = st.sidebar.date_input(
            "Start Date",
            value=date.today() - timedelta(days=30),
        )
        end_date = st.sidebar.date_input(
            "End Date",
            value=date.today(),
        )
        return start_date, end_date

    if filter_mode == "Full database":
        return queries.get_database_date_range()

    start_month_name = st.sidebar.selectbox(
        "Start Month",
        month_names,
        index=date.today().month - 2,
    )
    start_year = st.sidebar.selectbox(
        "Start Year",
        years,
        index=len(years) - 1,
    )
    end_month_name = st.sidebar.selectbox(
        "End Month",
        month_names,
        index=date.today().month - 1,
    )
    end_year = st.sidebar.selectbox(
        "End Year",
        years,
        index=len(years) - 1,
    )

    start_month_index = month_names.index(start_month_name) + 1
    end_month_index = month_names.index(end_month_name) + 1
    effective_start_date = date(start_year, start_month_index, 1)
    last_day = calendar.monthrange(end_year, end_month_index)[1]
    effective_end_date = date(end_year, end_month_index, last_day)
    return effective_start_date, effective_end_date


def _parse_transaction_preview_key(key):
    transaction_id, row_nr = key.split("|", 1)
    transaction_id = int(float(transaction_id)) if transaction_id else None
    if row_nr in ("", "nan", "None"):
        row_nr = None
    else:
        row_nr = int(float(row_nr))
    return transaction_id, row_nr


def get_dashboard_notification_reasons(page_title: str):
    notification_mode = settings.get("dashboard", {}).get("notification_mode", "Home only")
    if notification_mode == "Hide":
        return []
    if notification_mode == "Home only" and page_title != "Home":
        return []

    ignored_notifications = set(settings.get("dashboard", {}).get("ignored_notifications", []))
    notifications = []

    if queries.needs_calculated_account_balance_snapshots():
        notifications.append(
            {
                "id": "missing_calculated_account_balances",
                "level": "info",
                "message": (
                    "Some cash balances shown in the dashboard are calculated from transaction data because persistent account "
                    "balance snapshots are missing. Open Data Organizer > Account Balances > Calculate from Cash to persist these snapshots permanently."
                ),
            }
        )

    if queries.has_account_balances_with_missing_accounts():
        notifications.append(
            {
                "id": "orphaned_account_balances",
                "level": "warning",
                "message": (
                    "The balance snapshot table contains rows linked to accounts that no longer exist in the accounts table. "
                    "This can indicate stale or orphaned balance entries that should be reviewed in the Data Organizer."
                ),
            }
        )

    return [notification for notification in notifications if notification["id"] not in ignored_notifications]


def render_dashboard_notification_bar(page_title: str):
    notification_reasons = get_dashboard_notification_reasons(page_title)
    if not notification_reasons:
        return

    for notification in notification_reasons:
        level = notification.get("level", "info")
        message = notification.get("message", "")
        notification_id = notification.get("id")

        col1, col2 = st.columns([1, 0.1],)
        with col1:
            if level == "warning":
                st.warning(message)
            else:
                st.info(message)

        if notification_id:
            with col2:
                if st.button("Ignore", key=f"ignore_notification_{notification_id}"):
                    current_settings = load_settings()
                    ignored = current_settings.setdefault("dashboard", {}).get("ignored_notifications", [])
                    if notification_id not in ignored:
                        ignored.append(notification_id)
                        current_settings["dashboard"]["ignored_notifications"] = ignored
                        save_settings(current_settings)
                    st.rerun()


def _render_home_page():
    home_title = settings.get("home", {}).get("page_title", "Home")
    if home_title:
        st.header(home_title)

    render_dashboard_notification_bar("Home")
    st.sidebar.title("Home Filters")

    effective_start_date, effective_end_date = _get_date_range()

    timeline_scale = st.sidebar.radio(
        "Timeline scale",
        ["Linear", "Logarithmic"],
        index=0,
        help="Choose the vertical scale for the timeline chart.",
    )

    show_home_subheaders = settings.get("home", {}).get("show_chart_subheaders", True)

    st.markdown("---")
    col1, col2 = st.columns([1, 2])

    with col1:
        latest_timeline_distribution_pie(
            queries,
            start_date=effective_start_date,
            end_date=effective_end_date,
            show_subheader=show_home_subheaders,
        )

    with col2:
        df = timeline_line_chart(
            queries,
            start_date=effective_start_date,
            end_date=effective_end_date,
            scale_type=timeline_scale,
            show_subheader=show_home_subheaders,
        )

    if df is None:
        return

    latest_row = df.sort_values("Date").iloc[-1]
    st.markdown("---")
    col3, col4 = st.columns([1, 1])

    with col3:
        st.subheader("Latest timeline snapshot")
        st.metric("Latest Total", f"€{latest_row['Total']:,.2f}")
        st.metric("Snapshot Date", latest_row["Date"].strftime("%Y-%m-%d"))

    with col4:
        breakdown = pd.DataFrame(
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
        breakdown["Value"] = breakdown["Value"].map(lambda v: f"€{v:,.2f}")
        st.table(breakdown)


def _render_charts_page():
    st.header("Charts")
    st.sidebar.title("Chart Filters")

    chart_options = CHART_OPTIONS
    default_chart = settings.get("charts", {}).get("default_chart", "Timeline")

    pool_options = ["Cash", "Stocks", "Goods", "Interest"]
    selected_pools = st.sidebar.multiselect(
        "Pools",
        pool_options,
        default=pool_options,
        help="Select one or more pools to filter the available charts.",
    )
    if not selected_pools:
        st.sidebar.warning("No pools selected. Showing charts for all pools.")
        selected_pools = pool_options

    available_charts = [
        chart
        for chart in chart_options
        if set(selected_pools) & CHART_POOL_REQUIREMENTS.get(chart, set())
    ]
    if not available_charts:
        available_charts = chart_options

    chart = st.sidebar.selectbox(
        "Chart",
        available_charts,
        index=available_charts.index(default_chart) if default_chart in available_charts else 0,
        help="Choose a chart that is available for the selected pool(s).",
    )

    effective_start_date, effective_end_date = _get_date_range()

    timeline_scale = None
    if chart == "Timeline":
        timeline_scale = st.sidebar.radio(
            "Timeline scale",
            ["Linear", "Logarithmic"],
            index=0,
            help="Choose the vertical scale for the timeline chart.",
        )

    if chart == "Timeline":
        df = timeline_line_chart(
            queries,
            start_date=effective_start_date,
            end_date=effective_end_date,
            scale_type=timeline_scale,
            selected_pools=selected_pools,
        )
    elif chart == "Spending":
        df = spending_chart(
            queries,
            top_n=20,
            start_date=effective_start_date,
            end_date=effective_end_date,
        )
    elif chart == "Balances":
        hide_zero_balances = st.sidebar.checkbox(
            "Hide zero balances",
            value=True,
            help="Only show balances that are not equal to zero.",
        )
        df = balances_chart(
            queries,
            start_date=effective_start_date,
            end_date=effective_end_date,
            selected_pools=selected_pools,
            hide_zero_balances=hide_zero_balances,
        )
    elif chart == "Income vs Expenses":
        df = income_vs_expense_chart(
            queries,
            start_date=effective_start_date,
            end_date=effective_end_date,
        )
    elif chart == "Transaction Frequency":
        df = transaction_frequency_chart(
            queries,
            top_n=20,
        )
    elif chart == "Average Transaction":
        df = average_transaction_chart(
            queries,
            top_n=20,
        )
    elif chart == "Asset Allocation Trend":
        df = asset_allocation_trend_chart(
            queries,
            start_date=effective_start_date,
            end_date=effective_end_date,
            selected_pools=selected_pools,
        )
    elif chart == "Cash Flow Trend":
        df = monthly_cashflow_trend_chart(
            queries,
            start_date=effective_start_date,
            end_date=effective_end_date,
        )
    elif chart == "Category Drill-down":
        df = category_drilldown_chart(
            queries,
            start_date=effective_start_date,
            end_date=effective_end_date,
            top_n=20,
        )
    elif chart == "Account Balance History":
        df = account_balance_history_chart(
            queries,
            start_date=effective_start_date,
            end_date=effective_end_date,
            selected_pools=selected_pools,
        )
    elif chart == "Stock Portfolio Performance":
        df = stock_portfolio_performance_chart(
            queries,
        )
    elif chart == "Goods Valuation Change":
        df = goods_value_history_chart(
            queries,
        )
    elif chart == "Interest Growth":
        df = interest_growth_chart(
            queries,
        )
    elif chart == "Stock Positions":
        df = stock_positions_chart(
            queries,
            top_n=20,
        )
    elif chart == "Goods Valuation":
        df = goods_valuation_chart(
            queries,
            top_n=20,
        )
    elif chart == "Balance with Delta":
        df = balance_delta_chart(
            queries,
            top_n=20,
            selected_pools=selected_pools,
        )
    else:
        st.warning(
            "This is a draft Streamlit charts page. Only Timeline, Spending, Balances, Income vs Expenses, Transaction Frequency, Average Transaction, Stock Positions, Goods Valuation, and Balance with Delta are implemented for now."
        )
        return

    if df is None:
        return

    show_data_value = st.sidebar.checkbox(
        "Show underlying chart data",
        value=settings.get("charts", {}).get("show_underlying_data", False),
    )
    if show_data_value:
        st.dataframe(df)


def _render_pyplot_legacy_page():
    st.header("Pyplot (Legacy)")
    st.sidebar.title("Visualization Filters")

    chart = st.sidebar.selectbox(
        "Visualization",
        [
            "Timeline",
            "Spending",
            "Balances",
            "Income vs Expenses",
            "Transaction Frequency",
            "Average Transaction",
            "Stock Positions",
            "Stock Value History",
            "Goods Valuation",
            "Goods Value History",
            "Balance with Delta",
            "Interest Balance History",
        ],
        index=0,
    )

    top_n = st.sidebar.slider(
        "Top Categories",
        5,
        20,
        10,
    )

    minimum_amount = st.sidebar.number_input(
        "Minimum Amount",
        value=0.0,
    )

    show_table = st.sidebar.checkbox(
        "Show Data",
        False,
    )

    effective_start_date, effective_end_date = _get_date_range()
    df = None

    if chart == "Spending":
        df = charts_pyplot._pyplot_spending_chart(
            queries,
            top_n=top_n,
            start_date=effective_start_date,
            end_date=effective_end_date,
        )

    elif chart == "Balances":
        df = charts_pyplot._pyplot_account_balance_chart(queries)

    elif chart == "Income vs Expenses":
        df = charts_pyplot._pyplot_income_expense_chart(queries)

    elif chart == "Transaction Frequency":
        df = charts_pyplot._pyplot_transaction_frequency_chart(queries)

    elif chart == "Average Transaction":
        df = charts_pyplot._pyplot_average_transaction_chart(queries)

    elif chart == "Timeline":
        df = charts_pyplot._pyplot_balance_timeline_chart(
            queries,
            effective_start_date,
            effective_end_date,
        )

    elif chart == "Stock Positions":
        df = charts_pyplot._pyplot_stock_positions_chart(queries)

    elif chart == "Stock Value History":
        df = charts_pyplot._pyplot_stock_value_history_chart(queries)

    elif chart == "Goods Valuation":
        df = charts_pyplot._pyplot_depreciation_chart(queries)

    elif chart == "Goods Value History":
        df = charts_pyplot._pyplot_goods_value_history_chart(queries)

    elif chart == "Balance with Delta":
        df = charts_pyplot._pyplot_interest_balance_chart(queries)

    elif chart == "Interest Balance History":
        df = charts_pyplot._pyplot_interest_balance_history_chart(queries)

    if show_table and df is not None:
        st.subheader("Underlying Data")
        st.dataframe(df)


def _render_data_editor_page():
    from dashboard.data_editor import render_data_editor_sidebar

    pool = render_data_editor_sidebar(application_mode=application_mode, expert_mode=is_expert_mode)
    effective_start_date, effective_end_date = _get_date_range()
    render_data_editor_view(queries, effective_start_date, effective_end_date, pool, simple_mode=is_simple_mode)


def _render_merge_page():
    render_data_organizer_view(queries)


def _render_excel_import_page():
    st.header("Excel Import")
    render_import_view(db_path)

pages = [
    st.Page(_render_home_page, title="Home", icon="🏠", url_path="home", default=True),
    st.Page(_render_charts_page, title="Charts", icon="📈", url_path="charts"),
    st.Page(lambda: render_metrics_page(queries), title="Metrics", icon="📊", url_path="metrics"),
    st.Page(lambda: render_data_creator_view(queries), title="Data Creator", icon="🧩", url_path="data-creator"),
    st.Page(
        _render_data_editor_page,
        title="Data Viewer" if is_simple_mode else "Data Editor",
        icon="👁️" if is_simple_mode else "🧾",
        url_path="data-editor",
    ),
]

if not is_simple_mode:
    pages.append(st.Page(_render_merge_page, title="Data Organizer", icon="🔀", url_path="data-organizer"))

pages.append(st.Page(_render_excel_import_page, title="Excel Import", icon="📥", url_path="excel-import"))

if legacy_pyplots_enabled:
    pages.append(st.Page(_render_pyplot_legacy_page, title="Pyplot (Legacy)", icon="📊", url_path="pyplot-legacy"))

pages.append(st.Page(lambda: render_settings_view(db_path, queries, expert_mode=is_expert_mode), title="Settings", icon="⚙️", url_path="settings"))

selected_page = st.navigation(pages, position="sidebar")
if selected_page.title != "Home":
    render_dashboard_notification_bar(selected_page.title)
selected_page.run()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Income",
        f"€{queries.get_total_income():,.2f}"
    )

with col2:
    st.metric(
        "Expenses",
        f"€{abs(queries.get_total_expenses()):,.2f}"
    )

with col3:
    balance = sum(
        x[1]
        for x in queries.get_account_balances()
        if x[1] is not None
    )
    st.metric(
        "Net Balance",
        f"€{balance:,.2f}"
    )

