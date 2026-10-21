import streamlit as st

@st.cache_data(show_spinner=False)
def spending(queries):
    return queries.get_spending_by_category()

@st.cache_data(show_spinner=False)
def balances(queries):
    return queries.get_account_balances()

@st.cache_data(show_spinner=False)
def income(queries):
    return queries.get_total_income()

@st.cache_data(show_spinner=False)
def expenses(queries):
    return queries.get_total_expenses()

@st.cache_data(show_spinner=False)
def transaction_frequency(queries):
    return queries.get_transaction_frequency()

@st.cache_data(show_spinner=False)
def average_transactions(queries):
    return queries.get_average_transaction()

@st.cache_data(show_spinner=False)
def depreciation(queries):
    return queries.get_asset_depreciation()

@st.cache_data(show_spinner=False)
def balance_history(queries, start=None, end=None):
    return queries.get_balance_history(
        start_date=start,
        end_date=end,
    )

@st.cache_data(show_spinner=False)
def all_pools_timeline(queries, start=None, end=None):
    return queries.get_all_pools_timeline(
        start_date=start,
        end_date=end,
    )

@st.cache_data(show_spinner=False)
def latest_stock_positions(queries):
    return queries.get_latest_stock_positions()

@st.cache_data(show_spinner=False)
def stock_value_history(queries):
    return queries.get_stock_value_history()

@st.cache_data(show_spinner=False)
def latest_goods_valuations(queries):
    return queries.get_latest_goods_valuations()

@st.cache_data(show_spinner=False)
def goods_value_history(queries):
    return queries.get_goods_value_history()

@st.cache_data(show_spinner=False)
def latest_interest_balances(queries):
    return queries.get_latest_interest_balances()

@st.cache_data(show_spinner=False)
def interest_balance_history(queries):
    return queries.get_interest_balance_history()