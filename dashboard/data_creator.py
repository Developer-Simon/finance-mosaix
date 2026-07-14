import pandas as pd
import streamlit as st

from src.goods_depreciation import calculate_goods_current_value

POOL_COLUMN_CONFIG = {
    "Cash": [
        "Transaction ID",
        "Date",
        "Account",
        "Category",
        "Description",
        "Amount",
        "Balance After",
        "Source Sheet",
    ],
    "Stocks": [
        "Position ID",
        "Snapshot Date",
        "Name",
        "Ticker",
        "Quantity",
        "Price Previous",
        "Price Current",
        "Delta Value",
        "Delta Percent",
        "Position Value",
        "Depot Value Running",
        "Source Sheet",
    ],
    "Goods": [
        "Valuation ID",
        "Valuation Date",
        "Item Name",
        "Purchase Value",
        "Depreciation Input",
        "Value Previous",
        "Value Change",
        "Current Value",
        "Source Sheet",
    ],
    "Interest": [
        "Change ID",
        "Balance Date",
        "Account Name",
        "Balance",
        "Previous Balance",
        "Delta",
        "Source Sheet",
    ],
    "Account Balances": [
        "Balance ID",
        "Balance Date",
        "Account Name",
        "Balance",
        "Previous Balance",
        "Delta",
        "Entry Type",
        "Source Sheet",
    ],
}

NUMBER_COLUMNS = {
    "Transaction ID",
    "Position ID",
    "Valuation ID",
    "Change ID",
    "Balance ID",
    "Quantity",
    "Price Previous",
    "Price Current",
    "Delta Value",
    "Delta Percent",
    "Position Value",
    "Depot Value Running",
    "Purchase Value",
    "Depreciation Input",
    "Value Previous",
    "Value Change",
    "Current Value",
    "Balance After",
    "Balance",
    "Previous Balance",
    "Delta",
    "row_nr",
}

DATE_COLUMNS = {
    "Date",
    "Snapshot Date",
    "Valuation Date",
    "Balance Date",
}

POOL_SAVE_METHODS = {
    "Cash": "save_transactions",
    "Stocks": "save_stock_positions",
    "Goods": "save_goods_valuations",
    "Interest": "save_interest_balance_changes",
    "Account Balances": "save_account_balances",
}

POOL_INPUT_COLUMN_CONFIG = {
    "Cash": [
        "Description",
        "Category",
        "Amount",
        "Account",
        "Transaction ID",
        "Date",
    ],
    "Stocks": [
        "Snapshot Date",
        "Name",
        "Ticker",
        "Quantity",
        "Price Previous",
        "Price Current",
    ],
    "Goods": [
        "Valuation ID",
        "Valuation Date",
        "Item Name",
        "Purchase Value",
        "Depreciation Input",
        "Value Previous",
        "Value Change",
        "Current Value",
        "Source Sheet"
    ],
    "Interest": [
        "Change ID",
        "Balance Date",
        "Account Name",
        "Balance",
        "Previous Balance",
        "Delta",
        "Source Sheet",
    ],
    "Account Balances": [
        "Balance ID",
        "Balance Date",
        "Account Name",
        "Balance",
        "Previous Balance",
        "Delta",
        "Entry Type",
        "Source Sheet",
    ],
}

DEFAULT_SOURCE_SHEET = "manual"
POOL_DATE_COLUMN = {
    "Cash": "Date",
    "Stocks": "Snapshot Date",
    "Goods": "Valuation Date",
    "Interest": "Balance Date",
    "Account Balances": "Balance Date",
}


def _build_blank_input_table(pool: str, defaults: dict | None = None) -> pd.DataFrame:
    columns = POOL_INPUT_COLUMN_CONFIG[pool]
    if not columns:
        return pd.DataFrame()
    defaults = defaults or {}
    return pd.DataFrame([{col: defaults.get(col, pd.NA) for col in columns}])


def _is_missing(value) -> bool:
    return value in (None, "") or pd.isna(value)


def _get_latest_cash_balance_after(queries, queued_df: pd.DataFrame | None = None) -> float:
    if queued_df is not None and not queued_df.empty and "Balance After" in queued_df.columns:
        last_balance = queued_df["Balance After"].dropna()
        if not last_balance.empty:
            return float(last_balance.iloc[-1])

    try:
        row = queries.conn.execute(
            "SELECT balance_after FROM cash_transactions ORDER BY transaction_date DESC, transaction_id DESC LIMIT 1"
        ).fetchone()
        if row and row[0] is not None:
            return float(row[0])
    except Exception:
        pass

    return 0.0


def _get_next_transaction_id(queries, queued_df: pd.DataFrame | None = None) -> int:
    try:
        next_id = int(queries._next_id("cash_transactions", "transaction_id"))
    except Exception:
        next_id = int(
            queries.conn.execute("SELECT COALESCE(MAX(transaction_id), 0) + 1 FROM cash_transactions").fetchone()[0] or 1
        )

    if queued_df is not None and not queued_df.empty and "Transaction ID" in queued_df.columns:
        queued_ids = []
        for value in queued_df["Transaction ID"]:
            if pd.isna(value) or value == "":
                continue
            try:
                queued_ids.append(int(float(value)))
            except Exception:
                continue
        if queued_ids:
            next_id = max(next_id, max(queued_ids) + 1)

    return next_id


def _get_next_position_id(queries, queued_df: pd.DataFrame | None = None) -> int:
    try:
        next_id = int(queries._next_id("stock_positions", "position_id"))
    except Exception:
        next_id = int(
            queries.conn.execute("SELECT COALESCE(MAX(position_id), 0) + 1 FROM stock_positions").fetchone()[0] or 1
        )

    if queued_df is not None and not queued_df.empty and "Position ID" in queued_df.columns:
        queued_ids = []
        for value in queued_df["Position ID"]:
            if pd.isna(value) or value == "":
                continue
            try:
                queued_ids.append(int(float(value)))
            except Exception:
                continue
        if queued_ids:
            next_id = max(next_id, max(queued_ids) + 1)

    return next_id


def _get_next_interest_change_id(queries, queued_df: pd.DataFrame | None = None) -> int:
    try:
        next_id = int(queries._next_id("interest_balance_changes", "change_id"))
    except Exception:
        next_id = int(
            queries.conn.execute("SELECT COALESCE(MAX(change_id), 0) + 1 FROM interest_balance_changes").fetchone()[0] or 1
        )

    if queued_df is not None and not queued_df.empty and "Change ID" in queued_df.columns:
        queued_ids = []
        for value in queued_df["Change ID"]:
            if pd.isna(value) or value == "":
                continue
            try:
                queued_ids.append(int(float(value)))
            except Exception:
                continue
        if queued_ids:
            next_id = max(next_id, max(queued_ids) + 1)

    return next_id


def _get_next_account_balance_id(queries, queued_df: pd.DataFrame | None = None) -> int:
    try:
        next_id = int(queries._next_id("account_balances", "balance_id"))
    except Exception:
        next_id = int(
            queries.conn.execute("SELECT COALESCE(MAX(balance_id), 0) + 1 FROM account_balances").fetchone()[0] or 1
        )

    if queued_df is not None and not queued_df.empty and "Balance ID" in queued_df.columns:
        queued_ids = []
        for value in queued_df["Balance ID"]:
            if pd.isna(value) or value == "":
                continue
            try:
                queued_ids.append(int(float(value)))
            except Exception:
                continue
        if queued_ids:
            next_id = max(next_id, max(queued_ids) + 1)

    return next_id


def _get_stock_snapshot_prefill_for_date(queries, selected_date) -> pd.DataFrame:
    selected_date = pd.Timestamp(selected_date).date() if selected_date is not None else None
    if selected_date is None:
        return pd.DataFrame(columns=POOL_INPUT_COLUMN_CONFIG["Stocks"])

    row = queries.conn.execute(
        "SELECT MAX(snapshot_date) FROM stock_positions WHERE snapshot_date <= ?",
        [selected_date],
    ).fetchone()
    if not row or row[0] is None:
        return pd.DataFrame(columns=POOL_INPUT_COLUMN_CONFIG["Stocks"])

    snapshot_date = row[0]
    rows = queries.get_stock_positions_by_snapshot_date(snapshot_date)
    prefill_rows = []
    for row in rows:
        _, _, name, ticker, quantity, price_previous, price_current, *_ = row
        prefill_rows.append(
            {
                "Snapshot Date": selected_date,
                "Name": name,
                "Ticker": ticker,
                "Quantity": quantity,
                "Price Previous": price_current,
                "Price Current": pd.NA,
            }
        )

    if len(prefill_rows) == 0:
        prefill_rows.append({col: pd.NA for col in POOL_INPUT_COLUMN_CONFIG["Stocks"]})

    return pd.DataFrame(prefill_rows, columns=POOL_INPUT_COLUMN_CONFIG["Stocks"])


def _get_latest_stock_snapshot_prefill(queries) -> pd.DataFrame:
    return _get_stock_snapshot_prefill_for_date(queries, pd.Timestamp.today().date())


def _get_latest_goods_snapshot_prefill(queries) -> pd.DataFrame:
    latest_date = queries.conn.execute(
        "SELECT MAX(valuation_date) FROM goods_valuations"
    ).fetchone()
    if not latest_date or latest_date[0] is None:
        return pd.DataFrame(columns=POOL_INPUT_COLUMN_CONFIG["Goods"])

    try:
        next_valuation_id = int(queries._next_id("goods_valuations", "valuation_id"))
    except Exception:
        next_valuation_id = int(
            queries.conn.execute("SELECT COALESCE(MAX(valuation_id), 0) + 1 FROM goods_valuations").fetchone()[0] or 1
        )

    rows = queries.get_goods_valuations_by_valuation_date(latest_date[0])
    prefill_rows = []
    today = pd.Timestamp.today().date()
    for row in rows:
        (
            valuation_id,
            valuation_date,
            item_name,
            purchase_value,
            depreciation_input,
            value_previous,
            value_change,
            current_value,
            source_sheet,
            row_nr,
        ) = row
        previous_value = current_value if current_value is not None else value_previous
        months_diff = _months_between(latest_date[0], today)
        calculated_current_value = _calculate_goods_current_value(
            purchase_value,
            depreciation_input,
            previous_value,
            months_diff,
        )
        previous_value_numeric = 0.0
        if previous_value not in (None, "") and not pd.isna(previous_value):
            try:
                previous_value_numeric = float(previous_value)
            except Exception:
                previous_value_numeric = 0.0
        calculated_value_change = calculated_current_value - previous_value_numeric
        prefill_rows.append(
            {
                "Valuation ID": next_valuation_id,
                "Valuation Date": today,
                "Item Name": item_name,
                "Purchase Value": purchase_value,
                "Depreciation Input": depreciation_input,
                "Value Previous": previous_value,
                "Value Change": calculated_value_change,
                "Current Value": calculated_current_value,
                "Source Sheet": "Data Creator",
            }
        )
        next_valuation_id += 1

    if len(prefill_rows) == 0:
        prefill_rows.append({col: pd.NA for col in POOL_INPUT_COLUMN_CONFIG["Goods"]})

    return pd.DataFrame(prefill_rows, columns=POOL_INPUT_COLUMN_CONFIG["Goods"])


def _get_latest_interest_balance_prefill(queries) -> pd.DataFrame:
    latest_rows = queries.get_latest_interest_balances()
    if not latest_rows:
        return pd.DataFrame(columns=POOL_INPUT_COLUMN_CONFIG["Interest"])

    today = pd.Timestamp.today().date()
    next_change_id = _get_next_interest_change_id(queries, None)
    prefill_rows = []
    for _, account_name, balance, previous_balance, delta in latest_rows:
        previous_value = float(balance or 0.0)
        prefill_rows.append(
            {
                "Change ID": next_change_id,
                "Balance Date": today,
                "Account Name": account_name,
                "Balance": pd.NA,
                "Previous Balance": previous_value,
                "Delta": pd.NA,
                "Source Sheet": "Data Creator",
            }
        )
        next_change_id += 1

    if len(prefill_rows) == 0:
        prefill_rows.append({col: pd.NA for col in POOL_INPUT_COLUMN_CONFIG["Interest"]})

    return pd.DataFrame(prefill_rows, columns=POOL_INPUT_COLUMN_CONFIG["Interest"])


def _get_latest_account_balance_prefill(queries) -> pd.DataFrame:
    latest_rows = queries.get_latest_account_balances()
    if not latest_rows:
        return pd.DataFrame(columns=POOL_INPUT_COLUMN_CONFIG["Account Balances"])

    today = pd.Timestamp.today().date()
    next_balance_id = _get_next_account_balance_id(queries, None)
    prefill_rows = []
    for account_name, balance, previous_balance, delta, entry_type, source_sheet in latest_rows:
        previous_value = float(balance or 0.0)
        prefill_rows.append(
            {
                "Balance ID": next_balance_id,
                "Balance Date": today,
                "Account Name": account_name,
                "Balance": pd.NA,
                "Previous Balance": previous_value,
                "Delta": pd.NA,
                "Entry Type": "monitoring",
                "Source Sheet": "Data Creator",
            }
        )
        next_balance_id += 1

    if len(prefill_rows) == 0:
        prefill_rows.append({col: pd.NA for col in POOL_INPUT_COLUMN_CONFIG["Account Balances"]})

    return pd.DataFrame(prefill_rows, columns=POOL_INPUT_COLUMN_CONFIG["Account Balances"])


def _get_latest_interest_previous_balance(queries, account_name: str) -> float:
    rows = queries.get_interest_balance_changes_by_account_name(account_name)
    if not rows:
        return 0.0
    _, _, _, balance, _, _, _ = rows[0]
    try:
        return float(balance or 0.0)
    except Exception:
        return 0.0


def _get_latest_account_balance_previous_balance(queries, account_name: str) -> float:
    rows = queries.get_account_balance_entries_by_account_name(account_name)
    if not rows:
        return 0.0
    _, _, _, balance, _, _, _, _ = rows[0]
    try:
        return float(balance or 0.0)
    except Exception:
        return 0.0


def _get_latest_goods_valuation_for_item(queries, item_name: str):
    rows = queries.get_goods_valuations_by_item_name(item_name)
    if not rows:
        return None
    (
        valuation_id,
        valuation_date,
        item_name,
        purchase_value,
        depreciation_input,
        value_previous,
        value_change,
        current_value,
        source_sheet,
        row_nr,
    ) = rows[0]
    return {
        "valuation_date": valuation_date,
        "purchase_value": purchase_value,
        "depreciation_input": depreciation_input,
        "value_previous": value_previous,
        "current_value": current_value,
    }


def _months_between(start_date, end_date) -> int:
    if start_date is None or end_date is None:
        return 0
    start = pd.Timestamp(start_date).date()
    end = pd.Timestamp(end_date).date()
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


def _calculate_goods_current_value(purchase_value, depreciation_input, previous_value, months_diff: int) -> float:
    return calculate_goods_current_value(purchase_value, depreciation_input, previous_value, months_diff)


def _enrich_stock_rows(rows_to_add: pd.DataFrame, queries, queued_df: pd.DataFrame | None = None) -> pd.DataFrame:
    queued_df = queued_df if queued_df is not None else pd.DataFrame(columns=POOL_COLUMN_CONFIG["Stocks"])
    next_position_id = _get_next_position_id(queries, queued_df)
    current_rows = []
    last_depot_running = 0.0
    if not queued_df.empty and "Depot Value Running" in queued_df.columns:
        last_valid = queued_df["Depot Value Running"].dropna()
        if not last_valid.empty:
            last_depot_running = float(last_valid.iloc[-1])

    for _, row in rows_to_add.iterrows():
        if all(
            pd.isna(row.get(col)) or row.get(col) == ""
            for col in ["Snapshot Date", "Name", "Ticker", "Quantity", "Price Current"]
        ):
            continue

        quantity = row.get("Quantity")
        price_previous = row.get("Price Previous")
        price_current = row.get("Price Current")

        quantity_value = 0.0
        price_previous_value = 0.0
        price_current_value = 0.0
        try:
            if quantity is not None and quantity != "" and not pd.isna(quantity):
                quantity_value = float(quantity)
        except Exception:
            quantity_value = 0.0
        try:
            if price_current is not None and price_current != "" and not pd.isna(price_current):
                price_current_value = float(price_current)
        except Exception:
            price_current_value = 0.0
        try:
            if price_previous is not None and price_previous != "" and not pd.isna(price_previous):
                price_previous_value = float(price_previous)
            else:
                price_previous_value = price_current_value
        except Exception:
            price_previous_value = price_current_value

        position_value = quantity_value * price_current_value
        delta_value = (price_current_value - price_previous_value) * quantity_value
        delta_percent = 0.0
        if price_previous_value:
            delta_percent = ((price_current_value / price_previous_value) - 1) * 100

        last_depot_running += position_value
        enriched_row = row.to_dict()
        enriched_row["Price Previous"] = price_previous_value
        enriched_row["Position ID"] = next_position_id
        next_position_id += 1
        enriched_row["Source Sheet"] = "Data Creator"
        enriched_row["Price Current"] = price_current_value
        enriched_row["Delta Value"] = delta_value
        enriched_row["Delta Percent"] = delta_percent
        enriched_row["Position Value"] = position_value
        enriched_row["Depot Value Running"] = last_depot_running
        current_rows.append(enriched_row)

    return pd.DataFrame(current_rows, columns=POOL_COLUMN_CONFIG["Stocks"])


def _enrich_goods_rows(rows_to_add: pd.DataFrame, queries, queued_df: pd.DataFrame | None = None) -> pd.DataFrame:
    queued_df = queued_df if queued_df is not None else pd.DataFrame(columns=POOL_COLUMN_CONFIG["Goods"])
    next_valuation_id = 1
    try:
        next_valuation_id = int(queries._next_id("goods_valuations", "valuation_id"))
    except Exception:
        next_valuation_id = int(
            queries.conn.execute("SELECT COALESCE(MAX(valuation_id), 0) + 1 FROM goods_valuations").fetchone()[0] or 1
        )

    if not queued_df.empty and "Valuation ID" in queued_df.columns:
        queued_ids = []
        for value in queued_df["Valuation ID"]:
            if pd.isna(value) or value == "":
                continue
            try:
                queued_ids.append(int(float(value)))
            except Exception:
                continue
        if queued_ids:
            next_valuation_id = max(next_valuation_id, max(queued_ids) + 1)

    current_rows = []
    for _, row in rows_to_add.iterrows():
        if all(
            pd.isna(row.get(col)) or row.get(col) == ""
            for col in ["Valuation Date", "Item Name", "Purchase Value", "Depreciation Input"]
        ):
            continue

        valuation_date = row.get("Valuation Date")
        item_name = row.get("Item Name")
        purchase_value = row.get("Purchase Value")
        depreciation_input = row.get("Depreciation Input")
        value_previous = row.get("Value Previous")

        try:
            purchase_value = float(purchase_value) if not _is_missing(purchase_value) else 0.0
        except Exception:
            purchase_value = 0.0
        try:
            depreciation_input = float(depreciation_input) if not _is_missing(depreciation_input) else 0.0
        except Exception:
            depreciation_input = 0.0
        try:
            if not _is_missing(value_previous):
                value_previous = float(value_previous)
            else:
                value_previous = None
        except Exception:
            value_previous = None

        latest_item = _get_latest_goods_valuation_for_item(queries, item_name) if not _is_missing(item_name) else None
        latest_date = latest_item["valuation_date"] if latest_item is not None else valuation_date
        if latest_date is None:
            latest_date = valuation_date

        if value_previous is None:
            if latest_item is not None and latest_item.get("current_value") is not None:
                value_previous = latest_item["current_value"]
            else:
                value_previous = purchase_value

        months_diff = _months_between(latest_date, valuation_date)
        current_value = _calculate_goods_current_value(purchase_value, depreciation_input, value_previous, months_diff)
        value_change = current_value - value_previous

        enriched_row = row.to_dict()
        enriched_row["Valuation ID"] = next_valuation_id
        next_valuation_id += 1
        enriched_row["Current Value"] = current_value
        enriched_row["Value Previous"] = value_previous
        enriched_row["Value Change"] = value_change
        enriched_row["Source Sheet"] = "Data Creator"
        current_rows.append(enriched_row)

    return pd.DataFrame(current_rows, columns=POOL_COLUMN_CONFIG["Goods"])


def _column_config(columns: list[str]) -> dict[str, st.column_config.Column]:
    config = {}
    for column in columns:
        if column in NUMBER_COLUMNS:
            config[column] = st.column_config.NumberColumn(column, format="%f")
        elif column in DATE_COLUMNS:
            config[column] = st.column_config.DateColumn(column)
    return config


def _get_default_input_values(pool: str, queries) -> dict:
    defaults = {
        "Source Sheet": "Data Creator",
    }

    date_column = POOL_DATE_COLUMN.get(pool)
    if date_column:
        last_date_key = f"data_creator_last_date_{pool}"
        defaults[date_column] = st.session_state.get(last_date_key, pd.Timestamp.today().date())

    if pool == "Cash":
        next_id = st.session_state.get("data_creator_next_transaction_id")
        if next_id is None:
            next_id = _get_next_transaction_id(
                queries,
                st.session_state.get("data_creator_queue"),
            )
        defaults["Transaction ID"] = next_id
    elif pool == "Account Balances":
        next_id = st.session_state.get("data_creator_next_transaction_id")
        if next_id is None:
            next_id = _get_next_account_balance_id(
                queries,
                st.session_state.get("data_creator_queue"),
            )
        defaults["Balance ID"] = next_id

    return defaults


def _prepare_records(df: pd.DataFrame, pool: str) -> list[dict]:
    records = []
    for _, row in df.iterrows():
        record = {col: row.get(col) for col in POOL_COLUMN_CONFIG[pool]}
        if _is_missing(record.get("Source Sheet")):
            record["Source Sheet"] = DEFAULT_SOURCE_SHEET
        if _is_missing(record.get("row_nr")):
            record["row_nr"] = 0
        records.append(record)
    return records


def _normalize_input_rows(input_df: pd.DataFrame) -> pd.DataFrame:
    non_empty = input_df.dropna(how="all")
    if non_empty.empty:
        return non_empty
    return non_empty.reset_index(drop=True)


def render_data_creator_view(queries):
    st.header("Data Creator")
    st.sidebar.title("Data Creator")

    pool = st.sidebar.radio(
        "Pool",
        ["Cash", "Stocks", "Goods", "Interest", "Account Balances"],
        index=0,
        key="data_creator_pool",
    )

    if pd.isna(pool):
        pool = "Cash"

    editing_mode = False
    if pool == "Cash":
        editing_mode = st.sidebar.checkbox(
            "Table editing mode",
            value=False,
            help="Show the raw cash input table for manual editing.",
            key="data_creator_editing_mode",
        )

    previous_pool = st.session_state.get("data_creator_previous_pool")
    if pd.isna(previous_pool):
        previous_pool = None

    pool_changed = previous_pool != pool

    if "data_creator_queue" not in st.session_state or pool_changed:
        st.session_state.data_creator_queue = pd.DataFrame(columns=POOL_COLUMN_CONFIG[pool])

    if "data_creator_input_key_index" not in st.session_state or pool_changed:
        st.session_state.data_creator_input_key_index = 0
        st.session_state.data_creator_input_editor_key = f"data_creator_input_{pool}_0"
        st.session_state.data_creator_next_transaction_id = None

    if "data_creator_input" not in st.session_state or pool_changed:
        if pool == "Stocks":
            if "stock_creator_snapshot_date" not in st.session_state:
                st.session_state.stock_creator_snapshot_date = pd.Timestamp.today().date()
            if "stock_creator_snapshot_date_loaded" not in st.session_state:
                st.session_state.stock_creator_snapshot_date_loaded = pd.Timestamp.today().date()
            st.session_state.data_creator_input = _get_stock_snapshot_prefill_for_date(
                queries,
                st.session_state.stock_creator_snapshot_date,
            )
        elif pool == "Goods":
            st.session_state.data_creator_input = _get_latest_goods_snapshot_prefill(queries)
        elif pool == "Interest":
            st.session_state.data_creator_input = _get_latest_interest_balance_prefill(queries)
        elif pool == "Account Balances":
            st.session_state.data_creator_input = _get_latest_account_balance_prefill(queries)
        else:
            defaults = _get_default_input_values(pool, queries)
            st.session_state.data_creator_input = _build_blank_input_table(pool, defaults)
        st.session_state.data_creator_queue = pd.DataFrame(columns=POOL_COLUMN_CONFIG[pool])
        if pool == "Cash":
            st.session_state.data_creator_next_transaction_id = defaults.get("Transaction ID")
        elif pool == "Account Balances":
            st.session_state.data_creator_next_transaction_id = _get_next_account_balance_id(queries, st.session_state.data_creator_queue)

    if pool_changed:
        st.session_state.data_creator_previous_pool = pool

    if pool == "Stocks":
        st.write("Use the stock input form below to update current price or add a new stock. The snapshot table is read-only and can be collapsed.")

        existing_tickers = []
        if not st.session_state.data_creator_input.empty:
            existing_tickers = [
                str(t) for t in st.session_state.data_creator_input["Ticker"].dropna().unique()
            ]

        if "stock_creator_ticker_next" in st.session_state:
            next_ticker = st.session_state.pop("stock_creator_ticker_next")
            if next_ticker in existing_tickers:
                st.session_state["stock_creator_ticker"] = next_ticker

        st.subheader("Stock current price input")

        snapshot_date = st.date_input(
            "Snapshot Date",
            value=st.session_state.get("stock_creator_snapshot_date", pd.Timestamp.today().date()),
            key="stock_creator_snapshot_date",
        )
        if snapshot_date != st.session_state.get("stock_creator_snapshot_date_loaded"):
            st.session_state.stock_creator_snapshot_date_loaded = snapshot_date
            st.session_state.data_creator_input = _get_stock_snapshot_prefill_for_date(
                queries,
                snapshot_date,
            )
            st.session_state.stock_creator_ticker = ""
            st.session_state.stock_creator_quantity_changed = False
            st.session_state.stock_creator_use_quantity_total = False
            st.session_state.stock_creator_quantity_change = 0.0
            st.session_state.data_creator_input_key_index += 1
            st.session_state.data_creator_input_editor_key = f"data_creator_input_{pool}_{st.session_state.data_creator_input_key_index}"

        new_stock = st.checkbox(
            "Is this a new stock to be added?",
            key="stock_creator_new_stock",
        )

        if existing_tickers and not st.session_state.get("stock_creator_new_stock", False):
            stock_ticker = st.selectbox(
                "Ticker",
                options=existing_tickers,
                key="stock_creator_ticker",
            )
        else:
            stock_ticker = st.text_input(
                "Ticker",
                key="stock_creator_ticker",
            )

        price_current_default = st.session_state.get("stock_creator_price_current", 0.0)

        if st.session_state.get("stock_creator_new_stock", False):
            stock_name = st.text_input("Name", key="stock_creator_name")
            quantity = st.number_input(
                "Quantity",
                min_value=0.0,
                value=0.0,
                format="%f",
                key="stock_creator_quantity",
            )
            price_previous = st.number_input(
                "Price Previous",
                min_value=0.0,
                value=price_current_default,
                format="%f",
                key="stock_creator_price_previous",
            )
        else:
            stock_name = ""
            quantity = 0.0
            price_previous = 0.0
            stock_ticker_value = st.session_state.get("stock_creator_ticker", "")
            if stock_ticker_value in existing_tickers:
                selected_row = st.session_state.data_creator_input.loc[
                    st.session_state.data_creator_input["Ticker"] == stock_ticker_value
                ].iloc[0]
                stock_name = selected_row["Name"]
                quantity = selected_row["Quantity"]
                price_previous = selected_row["Price Previous"]
                existing_quantity = (
                    float(quantity)
                    if quantity is not None and quantity != "" and not pd.isna(quantity)
                    else 0.0
                )
                st.session_state["stock_creator_name"] = stock_name
                st.session_state["stock_creator_quantity"] = existing_quantity
                refresh_quantity_total = st.session_state.pop("stock_creator_refresh_quantity_total", False)
                if refresh_quantity_total and st.session_state.get("stock_creator_quantity_changed", False) and st.session_state.get("stock_creator_use_quantity_total", False):
                    st.session_state["stock_creator_quantity_total"] = existing_quantity
                st.session_state["stock_creator_price_previous"] = (
                    float(price_previous)
                    if price_previous is not None and price_previous != "" and not pd.isna(price_previous)
                    else price_current_default
                )
                st.text_input(
                    "Name",
                    value=stock_name,
                    disabled=True,
                    key="stock_creator_name",
                )
                quantity_changed = st.checkbox(
                    "Quantity changed?",
                    key="stock_creator_quantity_changed",
                )
                if quantity_changed:
                    use_total_quantity = st.checkbox(
                        "Enter total quantity instead of change",
                        key="stock_creator_use_quantity_total",
                    )
                else:
                    use_total_quantity = False
                    st.session_state["stock_creator_use_quantity_total"] = False

                if use_total_quantity:
                    quantity = st.number_input(
                        "Quantity",
                        min_value=0.0,
                        value=float(st.session_state.get("stock_creator_quantity_total", existing_quantity)),
                        format="%f",
                        key="stock_creator_quantity_total",
                    )
                else:
                    st.number_input(
                        "Quantity",
                        min_value=0.0,
                        value=existing_quantity,
                        disabled=True,
                        format="%f",
                        key="stock_creator_quantity",
                    )
                    if quantity_changed:
                        quantity_change = st.number_input(
                            "Quantity change",
                            min_value=-existing_quantity,
                            value=float(st.session_state.get("stock_creator_quantity_change", 0.0)),
                            format="%f",
                            key="stock_creator_quantity_change",
                        )
                        quantity = existing_quantity + quantity_change
                    else:
                        quantity = existing_quantity
                st.number_input(
                    "Price Previous",
                    min_value=0.0,
                    value=float(price_previous) if price_previous is not None and price_previous != "" and not pd.isna(price_previous) else price_current_default,
                    disabled=True,
                    format="%f",
                    key="stock_creator_price_previous",
                )
            else:
                st.warning(
                    "Ticker not found in existing stock snapshot. Mark as new stock to add it."
                )
                stock_name = st.text_input("Name", key="stock_creator_name")
                quantity = st.number_input(
                    "Quantity",
                    min_value=0.0,
                    value=0.0,
                    format="%f",
                    key="stock_creator_quantity",
                )
                price_previous = st.number_input(
                    "Price Previous",
                    min_value=0.0,
                    value=price_current_default,
                    format="%f",
                    key="stock_creator_price_previous",
                )

        price_current = st.number_input(
            "Price Current",
            min_value=0.0,
            value=price_current_default,
            format="%f",
            key="stock_creator_price_current",
        )

        add_stock = st.button(
            "Add stock row",
            width="stretch",
            type="secondary",
            key="stock_creator_add_stock",
        )

        with st.expander("Stock snapshot preview", expanded=False):
            st.data_editor(
                st.session_state.data_creator_input,
                width="stretch",
                hide_index=True,
                num_rows="fixed",
                column_config=_column_config(POOL_INPUT_COLUMN_CONFIG[pool]),
                key=st.session_state.data_creator_input_editor_key,
                disabled=True,
            )
    elif pool == "Goods":
        st.write("Use the goods input form below to add or update depreciation valuations. The preview table shows existing goods with the latest current value.")

        add_snapshot_rows = False
        if st.session_state.data_creator_input.empty:
            st.info("No existing goods snapshot available. Enter a new goods valuation row below.")
        else:
            st.subheader("Existing goods snapshot preview")
            st.data_editor(
                st.session_state.data_creator_input,
                width="stretch",
                hide_index=True,
                num_rows="fixed",
                column_config=_column_config(POOL_INPUT_COLUMN_CONFIG[pool]),
                key=f"data_creator_goods_preview",
                disabled=True,
            )
            add_snapshot_rows = st.button(
                "Add goods snapshot rows",
                width="stretch",
                type="secondary",
                key="goods_creator_add_snapshot_rows",
            )

        with st.expander("Goods valuation input", expanded=False):
            valuation_date = st.date_input(
                "Valuation Date",
                value=pd.Timestamp.today().date(),
                key="goods_creator_valuation_date",
            )
            item_name = st.text_input(
                "Item Name",
                value=st.session_state.get("goods_creator_item_name", ""),
                key="goods_creator_item_name",
            )
            purchase_value = st.number_input(
                "Purchase Value",
                min_value=0.0,
                value=float(st.session_state.get("goods_creator_purchase_value", 0.0)),
                format="%f",
                key="goods_creator_purchase_value",
            )
            depreciation_input = st.number_input(
                "Depreciation Input",
                min_value=0.0,
                value=float(st.session_state.get("goods_creator_depreciation_input", 0.0)),
                format="%f",
                key="goods_creator_depreciation_input",
            )

            add_goods = st.button(
                "Add goods valuation row",
                width="stretch",
                type="secondary",
                key="goods_creator_add_goods",
            )

        add_to_queue = False

    elif pool == "Interest":
        st.write("Use the interest input form below to update existing account balances or add a new account. The snapshot preview table is read-only and can be collapsed.")

        existing_accounts = queries.get_interest_account_names()
        if "interest_creator_account_next" in st.session_state:
            next_account = st.session_state.pop("interest_creator_account_next")
            if next_account in existing_accounts:
                st.session_state["interest_creator_account_name"] = next_account

        with st.form("interest_creator_form", clear_on_submit=False):
            new_account = st.checkbox(
                "Is this a new account?",
                key="interest_creator_new_account",
            )

            if new_account or not existing_accounts:
                account_name = st.text_input(
                    "Account Name",
                    value=st.session_state.get("interest_creator_account_name", ""),
                    key="interest_creator_account_name",
                )
            else:
                account_name = st.selectbox(
                    "Account Name",
                    options=existing_accounts,
                    index=existing_accounts.index(st.session_state.get("interest_creator_account_name", existing_accounts[0]))
                    if st.session_state.get("interest_creator_account_name") in existing_accounts
                    else 0,
                    key="interest_creator_account_name",
                )

            balance_date = st.date_input(
                "Balance Date",
                value=pd.Timestamp.today().date(),
                key="interest_creator_balance_date",
            )

            previous_balance = 0.0
            if account_name and not new_account:
                previous_balance = _get_latest_interest_previous_balance(queries, account_name)

            st.metric("Previous Balance", f"{previous_balance:.2f}")

            balance = st.number_input(
                "Balance",
                min_value=0.0,
                value=float(st.session_state.get("interest_creator_balance", 0.0)),
                format="%f",
                key="interest_creator_balance",
            )

            delta = balance - previous_balance
            st.metric("Delta", f"{delta:.2f}")

            add_interest = st.form_submit_button(
                "Add interest balance row",
                width="stretch",
                type="secondary",
                key="interest_creator_add_interest",
            )

        with st.expander("Interest snapshot preview", expanded=False):
            st.data_editor(
                st.session_state.data_creator_input,
                width="stretch",
                hide_index=True,
                num_rows="fixed",
                column_config=_column_config(POOL_INPUT_COLUMN_CONFIG[pool]),
                key=f"data_creator_interest_preview",
                disabled=True,
            )

        add_to_queue = False

    elif pool == "Account Balances":
        st.write("Use the account balance input form below to add monitoring or calculated account balance snapshots.")

        existing_accounts = queries.get_active_account_names()
        new_account = st.checkbox(
            "Is this a new account?",
            key="account_balance_creator_new_account",
        )

        if new_account or not existing_accounts:
            account_name = st.text_input(
                "Account Name",
                value=st.session_state.get("account_balance_creator_account_name", ""),
                key="account_balance_creator_account_name",
            )
        else:
            account_name = st.selectbox(
                "Account Name",
                options=existing_accounts,
                index=existing_accounts.index(st.session_state.get("account_balance_creator_account_name", existing_accounts[0]))
                if st.session_state.get("account_balance_creator_account_name") in existing_accounts
                else 0,
                key="account_balance_creator_account_name",
            )

        balance_date = st.date_input(
            "Balance Date",
            value=pd.Timestamp.today().date(),
            key="account_balance_creator_balance_date",
        )

        entry_type = st.selectbox(
            "Entry Type",
            ["monitoring", "calculated"],
            index=0,
            key="account_balance_creator_entry_type",
        )

        previous_balance = 0.0
        if account_name and not new_account:
            previous_balance = _get_latest_account_balance_previous_balance(queries, account_name)

        st.metric("Previous Balance", f"{previous_balance:.2f}")

        balance = st.number_input(
            "Balance",
            min_value=0.0,
            value=float(st.session_state.get("account_balance_creator_balance", 0.0)),
            format="%f",
            key="account_balance_creator_balance",
        )

        delta = balance - previous_balance
        st.metric("Delta", f"{delta:.2f}")

        add_account_balance = st.button(
            "Add account balance row",
            width="stretch",
            type="secondary",
            key="account_balance_creator_add_account_balance",
        )

        with st.expander("Account Balance snapshot preview", expanded=False):
            st.data_editor(
                st.session_state.data_creator_input,
                width="stretch",
                hide_index=True,
                num_rows="fixed",
                column_config=_column_config(POOL_INPUT_COLUMN_CONFIG[pool]),
                key=f"data_creator_account_balance_preview",
                disabled=True,
            )

        add_to_queue = False

    elif pool == "Cash":
        if editing_mode:
            st.write("Editing mode enabled: use the raw cash input table to edit and queue transactions.")
            with st.form("data_creator_input_form", clear_on_submit=False):
                input_df = st.data_editor(
                    st.session_state.data_creator_input,
                    width="stretch",
                    hide_index=True,
                    num_rows="dynamic",
                    column_config=_column_config(POOL_INPUT_COLUMN_CONFIG[pool]),
                    key=st.session_state.data_creator_input_editor_key,
                )
                add_to_queue = st.form_submit_button(
                    "Add queued rows",
                    width="stretch",
                    type="secondary",
                )
            st.session_state.data_creator_input = input_df
            add_cash = False
        else:
            st.write("Use the cash transaction form below. Enable table editing mode in the sidebar to replace the form with the raw cash input table.")

            existing_accounts = queries.get_active_account_names()
            existing_categories = queries.get_category_names()
            date_value = st.session_state.get(
                "data_creator_last_date_Cash",
                pd.Timestamp.today().date(),
            )
            next_transaction_id = _get_next_transaction_id(queries, st.session_state.data_creator_queue)

            with st.form("cash_creator_form", clear_on_submit=False):
                new_account = st.checkbox(
                    "Is this a new account?",
                    key="cash_creator_new_account",
                )
                if new_account or not existing_accounts:
                    account = st.text_input(
                        "Account",
                        value=st.session_state.get("cash_creator_account", ""),
                        key="cash_creator_account",
                    )
                else:
                    account = st.selectbox(
                        "Account",
                        options=existing_accounts,
                        index=0,
                        key="cash_creator_account",
                    )

                new_category = st.checkbox(
                    "Is this a new category?",
                    key="cash_creator_new_category",
                )
                if new_category or not existing_categories:
                    category = st.text_input(
                        "Category",
                        value=st.session_state.get("cash_creator_category", ""),
                        key="cash_creator_category",
                    )
                else:
                    category = st.selectbox(
                        "Category",
                        options=existing_categories,
                        index=0,
                        key="cash_creator_category",
                    )

                description = st.text_input(
                    "Description",
                    value=st.session_state.get("cash_creator_description", ""),
                    key="cash_creator_description",
                )

                amount = st.number_input(
                    "Amount",
                    min_value=-999999999.0,
                    value=st.session_state.get("cash_creator_amount", 0.0),
                    format="%f",
                    key="cash_creator_amount",
                )

                transaction_date = st.date_input(
                    "Date",
                    value=date_value,
                    key="cash_creator_date",
                )

                st.markdown(f"**Transaction ID:** {next_transaction_id}")

                add_cash = st.form_submit_button(
                    "Add cash transaction",
                    width="stretch",
                    type="secondary",
                )
            add_to_queue = False
    else:
        st.write("Enter data in the table below, use Tab to move between cells, and press Enter or click the button to add rows to the queue.")

        with st.form("data_creator_input_form", clear_on_submit=False):
            input_df = st.data_editor(
                st.session_state.data_creator_input,
                width="stretch",
                hide_index=True,
                num_rows="dynamic",
                column_config=_column_config(POOL_INPUT_COLUMN_CONFIG[pool]),
                key=st.session_state.data_creator_input_editor_key,
            )
            add_to_queue = st.form_submit_button(
                "Add queued rows",
                width="stretch",
                type="secondary",
            )

        st.session_state.data_creator_input = input_df
        add_cash = False

    if pool == "Stocks" and add_stock:
        if not stock_ticker or stock_ticker == "":
            st.warning("Enter a ticker for the stock row.")
        elif not new_stock and stock_ticker not in existing_tickers:
            st.warning("Select an existing ticker or mark the row as a new stock.")
        else:
            form_row = {
                "Snapshot Date": snapshot_date,
                "Name": stock_name,
                "Ticker": stock_ticker,
                "Quantity": quantity,
                "Price Previous": price_previous,
                "Price Current": price_current,
            }
            rows_to_add = pd.DataFrame([form_row], columns=POOL_INPUT_COLUMN_CONFIG["Stocks"])
            rows_to_add = _enrich_stock_rows(rows_to_add, queries, st.session_state.data_creator_queue)
            if rows_to_add.empty:
                st.warning("Could not add the stock row. Check the input values.")
            else:
                st.session_state.data_creator_queue = pd.concat(
                    [st.session_state.data_creator_queue, rows_to_add],
                    ignore_index=True,
                )
                st.success("Added stock row to the queue.")
                if not new_stock and stock_ticker in existing_tickers:
                    current_index = existing_tickers.index(stock_ticker)
                    next_index = (current_index + 1) % len(existing_tickers)
                    st.session_state["stock_creator_ticker_next"] = existing_tickers[next_index]
                    st.session_state["stock_creator_refresh_quantity_total"] = True
                st.session_state.data_creator_input_key_index += 1
                st.session_state.data_creator_input_editor_key = f"data_creator_input_{pool}_{st.session_state.data_creator_input_key_index}"
                st.rerun()

    if pool == "Goods" and add_goods:
        if not item_name or item_name == "":
            st.warning("Enter an item name for the goods row.")
        else:
            form_row = {
                "Valuation Date": valuation_date,
                "Item Name": item_name,
                "Purchase Value": purchase_value,
                "Depreciation Input": depreciation_input,
                "Value Previous": purchase_value,
                "Value Change": 0.0,
                "Current Value": None,
            }
            rows_to_add = pd.DataFrame([form_row], columns=POOL_INPUT_COLUMN_CONFIG["Goods"])
            rows_to_add = _enrich_goods_rows(rows_to_add, queries, st.session_state.data_creator_queue)
            if rows_to_add.empty:
                st.warning("Could not add the goods valuation row. Check the input values.")
            else:
                st.session_state.data_creator_queue = pd.concat(
                    [st.session_state.data_creator_queue, rows_to_add],
                    ignore_index=True,
                )
                st.success("Added goods valuation row to the queue.")
                st.session_state.data_creator_input_key_index += 1
                st.session_state.data_creator_input_editor_key = f"data_creator_input_{pool}_{st.session_state.data_creator_input_key_index}"
                st.rerun()

    if pool == "Goods" and add_snapshot_rows:
        rows_to_add = _normalize_input_rows(st.session_state.data_creator_input)
        if rows_to_add.empty:
            st.warning("No goods snapshot rows available to add.")
        else:
            st.session_state.data_creator_queue = pd.concat(
                [st.session_state.data_creator_queue, rows_to_add],
                ignore_index=True,
            )
            st.success("Added goods snapshot rows to the queue.")
            st.session_state.data_creator_input_key_index += 1
            st.session_state.data_creator_input_editor_key = f"data_creator_input_{pool}_{st.session_state.data_creator_input_key_index}"
            st.rerun()

    if pool == "Cash" and add_cash:
        if not account or account == "":
            st.warning("Enter an account name.")
        elif not category or category == "":
            st.warning("Enter a category.")
        else:
            queued = st.session_state.data_creator_queue
            last_balance = _get_latest_cash_balance_after(queries, queued)
            amount_value = 0.0
            if amount is not None and amount != "" and not pd.isna(amount):
                try:
                    amount_value = float(amount)
                except Exception:
                    amount_value = 0.0

            last_balance += amount_value
            form_row = {
                "Transaction ID": next_transaction_id,
                "Date": transaction_date,
                "Account": account,
                "Category": category,
                "Description": description,
                "Amount": amount,
                "Balance After": last_balance,
                "Source Sheet": "Data Creator",
            }
            queued = pd.concat([queued, pd.DataFrame([form_row], columns=POOL_COLUMN_CONFIG["Cash"])], ignore_index=True)
            st.session_state.data_creator_queue = queued
            st.success("Added cash transaction to the queue.")
            st.session_state.data_creator_next_transaction_id = _get_next_transaction_id(queries, st.session_state.data_creator_queue)
            st.session_state.data_creator_input_key_index += 1
            st.session_state.data_creator_input_editor_key = f"data_creator_input_{pool}_{st.session_state.data_creator_input_key_index}"
            st.rerun()

    if pool == "Interest" and add_interest:
        if not account_name or account_name == "":
            st.warning("Enter an account name.")
        else:
            balance_value = 0.0
            if balance is not None and balance != "" and not pd.isna(balance):
                try:
                    balance_value = float(balance)
                except Exception:
                    balance_value = 0.0

            delta_value = balance_value - previous_balance
            change_id = _get_next_interest_change_id(queries, st.session_state.data_creator_queue)
            form_row = {
                "Change ID": change_id,
                "Balance Date": balance_date,
                "Account Name": account_name,
                "Balance": balance_value,
                "Previous Balance": previous_balance,
                "Delta": delta_value,
                "Source Sheet": "Data Creator",
            }
            queued = pd.concat([st.session_state.data_creator_queue, pd.DataFrame([form_row], columns=POOL_COLUMN_CONFIG["Interest"])], ignore_index=True)
            st.session_state.data_creator_queue = queued
            st.success("Added interest balance row to the queue.")
            if not new_account and existing_accounts:
                try:
                    current_index = existing_accounts.index(account_name)
                    next_index = (current_index + 1) % len(existing_accounts)
                    st.session_state["interest_creator_account_next"] = existing_accounts[next_index]
                except ValueError:
                    pass
            st.session_state.data_creator_input_key_index += 1
            st.session_state.data_creator_input_editor_key = f"data_creator_input_{pool}_{st.session_state.data_creator_input_key_index}"
            st.rerun()

    if pool == "Account Balances" and add_account_balance:
        if not account_name or account_name == "":
            st.warning("Enter an account name.")
        else:
            balance_value = 0.0
            if balance is not None and balance != "" and not pd.isna(balance):
                try:
                    balance_value = float(balance)
                except Exception:
                    balance_value = 0.0

            delta_value = balance_value - previous_balance
            balance_id = _get_next_account_balance_id(queries, st.session_state.data_creator_queue)
            form_row = {
                "Balance ID": balance_id,
                "Balance Date": balance_date,
                "Account Name": account_name,
                "Balance": balance_value,
                "Previous Balance": previous_balance,
                "Delta": delta_value,
                "Entry Type": entry_type,
                "Source Sheet": "Data Creator",
            }
            queued = pd.concat([st.session_state.data_creator_queue, pd.DataFrame([form_row], columns=POOL_COLUMN_CONFIG["Account Balances"])], ignore_index=True)
            st.session_state.data_creator_queue = queued
            st.success("Added account balance row to the queue.")
            st.session_state.data_creator_input_key_index += 1
            st.session_state.data_creator_input_editor_key = f"data_creator_input_{pool}_{st.session_state.data_creator_input_key_index}"
            st.rerun()

    if pool != "Stocks" and add_to_queue:
        rows_to_add = _normalize_input_rows(input_df)
        if rows_to_add.empty:
            st.warning("Enter at least one row before adding to the queue.")
        else:
            for _, row in rows_to_add.iterrows():
                date_column = POOL_DATE_COLUMN.get(pool)
                if date_column:
                    last_date_key = f"data_creator_last_date_{pool}"
                    date_value = row.get(date_column)
                    if date_value is not None and date_value != "" and not pd.isna(date_value):
                        st.session_state[last_date_key] = date_value

            if pool == "Cash":
                queued = st.session_state.data_creator_queue
                last_balance = _get_latest_cash_balance_after(queries, queued)
                enriched_rows = []
                for _, row in rows_to_add.iterrows():
                    amount = row.get("Amount")
                    amount_value = 0.0
                    if amount is not None and amount != "" and not pd.isna(amount):
                        try:
                            amount_value = float(amount)
                        except Exception:
                            amount_value = 0.0

                    last_balance += amount_value
                    enriched_row = row.to_dict()
                    enriched_row["Balance After"] = last_balance
                    enriched_row["Source Sheet"] = "Data Creator"
                    enriched_rows.append(enriched_row)

                rows_to_add = pd.DataFrame(enriched_rows, columns=POOL_COLUMN_CONFIG[pool])
            else:
                rows_to_add = rows_to_add.astype(object).where(pd.notna(rows_to_add), None)
                enriched_rows = []
                for _, row in rows_to_add.iterrows():
                    enriched_row = row.to_dict()
                    enriched_row["Source Sheet"] = enriched_row.get("Source Sheet") or "Data Creator"
                    enriched_rows.append(enriched_row)
                rows_to_add = pd.DataFrame(enriched_rows, columns=POOL_COLUMN_CONFIG[pool])

            queued = st.session_state.data_creator_queue
            st.session_state.data_creator_queue = pd.concat([queued, rows_to_add], ignore_index=True)
            if pool == "Cash":
                st.session_state.data_creator_next_transaction_id = _get_next_transaction_id(queries, st.session_state.data_creator_queue)

            st.session_state.data_creator_input_key_index += 1
            st.session_state.data_creator_input_editor_key = f"data_creator_input_{pool}_{st.session_state.data_creator_input_key_index}"
            defaults = _get_default_input_values(pool, queries)
            st.session_state.data_creator_input = _build_blank_input_table(pool, defaults)
            st.rerun()

    st.write("---")
    st.subheader("To be added")

    if st.session_state.data_creator_queue.empty:
        st.info("No queued rows yet. Enter data above and add rows to the queue.")
    else:
        queued_df = st.data_editor(
            st.session_state.data_creator_queue,
            width="stretch",
            hide_index=True,
            column_config=_column_config(POOL_COLUMN_CONFIG[pool]),
            key=f"data_creator_queue_{pool}",
        )
        st.session_state.data_creator_queue = queued_df

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Clear queued rows", type="secondary"):
                st.session_state.data_creator_queue = pd.DataFrame(columns=POOL_COLUMN_CONFIG[pool])
                st.success("Cleared queued rows.")
                st.rerun()
        with col2:
            if st.button("Save queued rows to database", type="primary"):
                records = _prepare_records(st.session_state.data_creator_queue, pool)
                save_method = POOL_SAVE_METHODS[pool]
                saved_count = getattr(queries, save_method)(records)
                st.session_state.data_creator_queue = pd.DataFrame(columns=POOL_COLUMN_CONFIG[pool])
                st.success(f"Saved {saved_count} queued row(s) to the database.")
        with col3:
            st.write("\n")
            st.write("\n")
            st.metric("Queued rows", len(st.session_state.data_creator_queue))
