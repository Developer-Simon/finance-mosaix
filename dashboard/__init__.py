"""
Finance dashboard package.
"""

import importlib

from .charts import (
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
_import_module = importlib.import_module(__name__ + ".import")
render_import_view = _import_module.render_import_view
from .metrics import render_metrics_page
from .data_creator import render_data_creator_view
from .data_editor import render_data_editor_view
from .data_organizer import render_data_organizer_view
from .settings import CHART_OPTIONS, render_settings_view, load_settings, save_settings

__all__ = [
    "timeline_line_chart",
    "latest_timeline_distribution_pie",
    "spending_chart",
    "balances_chart",
    "income_vs_expense_chart",
    "transaction_frequency_chart",
    "average_transaction_chart",
    "asset_allocation_trend_chart",
    "monthly_cashflow_trend_chart",
    "category_drilldown_chart",
    "account_balance_history_chart",
    "stock_portfolio_performance_chart",
    "goods_value_history_chart",
    "interest_growth_chart",
    "stock_positions_chart",
    "goods_valuation_chart",
    "balance_delta_chart",
    "render_import_view",
    "render_metrics_page",
    "render_data_creator_view",
    "render_data_editor_view",
    "render_data_organizer_view",
    "CHART_OPTIONS",
    "render_settings_view",
    "load_settings",
    "save_settings",
]
