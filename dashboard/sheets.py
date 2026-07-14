import pandas as pd
import streamlit as st

VISIBLE_COLUMNS = [
    "Transaction ID",
    "Date",
    "Account",
    "Category",
    "Description",
    "Amount",
    "Balance After",
    "Source Sheet",
]

HIDDEN_COLUMNS = [
    "original_key",
    "account_id",
    "category_id",
    "row_nr",
]

ALL_COLUMNS = VISIBLE_COLUMNS + HIDDEN_COLUMNS


def build_transaction_sheet(rows):
    df = pd.DataFrame(
        rows,
        columns=[
            "Transaction ID",
            "Date",
            "Account",
            "Category",
            "Description",
            "Amount",
            "Balance After",
            "Source Sheet",
            "account_id",
            "category_id",
            "row_nr",
        ],
    )

    if df.empty:
        df = pd.DataFrame(columns=VISIBLE_COLUMNS)
        df.index.name = "original_key"
        return df

    df["original_key"] = (
        df["Transaction ID"].astype(str)
        + "|"
        + df["account_id"].astype(str)
        + "|"
        + df["category_id"].astype(str)
    )

    df = df.set_index("original_key")
    df.index = df.index.astype(str)
    return df[VISIBLE_COLUMNS]


def build_transaction_preview_sheet(rows):
    df = pd.DataFrame(
        rows,
        columns=[
            "Transaction ID",
            "Date",
            "Account",
            "Category",
            "Description",
            "Amount",
            "Balance After",
            "Source Sheet",
            "account_id",
            "category_id",
            "row_nr",
        ],
    )

    if df.empty:
        df = pd.DataFrame(columns=VISIBLE_COLUMNS)
        df.index.name = "preview_key"
        return df

    df["preview_key"] = (
        df["Transaction ID"].astype(str)
        + "|"
        + df["account_id"].astype(str)
        + "|"
        + df["category_id"].astype(str)
        + "|"
        + df["row_nr"].astype(str)
    )

    df = df.set_index("preview_key")
    df.index = df.index.astype(str)
    return df[VISIBLE_COLUMNS]


def build_pool_sheet(rows, columns, index_cols, visible_columns):
    df = pd.DataFrame(rows, columns=columns)

    if df.empty:
        df = pd.DataFrame(columns=visible_columns)
        df.index.name = "original_key"
        return df

    if isinstance(index_cols, str):
        index_cols = [index_cols]

    df["original_key"] = df[index_cols].astype(str).agg("|".join, axis=1)
    df = df.set_index("original_key")
    df.index = df.index.astype(str)
    return df[visible_columns]


def render_transaction_sheet(df, key="transaction_sheet"):
    column_config = {
        "Transaction ID": st.column_config.NumberColumn("Transaction ID", format="%d"),
        "Amount": st.column_config.NumberColumn("Amount", format="%f"),
        "Balance After": st.column_config.NumberColumn("Balance After", format="%f"),
        "Date": st.column_config.DateColumn("Date"),
    }

    edited = st.data_editor(
        df,
        width="stretch",
        hide_index=True,
        column_config=column_config,
        key=key,
    )

    return edited


def render_data_sheet(df, key="data_sheet"):
    column_config = {}
    number_columns = {
        "Transaction ID",
        "Position ID",
        "Valuation ID",
        "Change ID",
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
    date_columns = {
        "Date",
        "Snapshot Date",
        "Valuation Date",
        "Balance Date",
    }

    for column in df.columns:
        if column in number_columns:
            column_config[column] = st.column_config.NumberColumn(column, format="%f")
        elif column in date_columns:
            column_config[column] = st.column_config.DateColumn(column)

    edited = st.data_editor(
        df,
        width="stretch",
        hide_index=True,
        column_config=column_config,
        key=key,
    )

    return edited


def _rows_equal(left, right):
    for column in VISIBLE_COLUMNS:
        left_value = left[column]
        right_value = right[column]

        if pd.isna(left_value) and pd.isna(right_value):
            continue

        if isinstance(left_value, pd.Timestamp) and isinstance(right_value, pd.Timestamp):
            if left_value.date() != right_value.date():
                return False
            continue

        if left_value != right_value:
            return False

    return True


def _add_selection_column(df):
    if df.empty or "Selected" in df.columns:
        return df

    df = df.copy()
    df.insert(0, "Selected", True)
    return df


def build_transaction_diff(original_df, edited_df, selected=False):
    columns = ["Change Type", "Transaction ID", "Field", "Before", "After"]
    if selected:
        columns = ["Selected", "Record Key"] + columns

    if original_df is None or edited_df is None:
        diff_df = pd.DataFrame(columns=columns)
        return _add_selection_column(diff_df) if selected else diff_df

    original_map = {str(index): row for index, row in original_df.iterrows()}
    edited_map = {str(index): row for index, row in edited_df.iterrows()}

    diff_rows = []
    for original_key, edited in edited_df.iterrows():
        original_key = str(original_key)
        if original_key not in original_map:
            row = {
                "Change Type": "Added",
                "Transaction ID": edited.get("Transaction ID"),
                "Field": "Row",
                "Before": None,
                "After": edited[VISIBLE_COLUMNS].to_dict(),
            }
            if selected:
                row["Record Key"] = original_key
            diff_rows.append(row)
            continue

        original = original_map[original_key]
        for column in VISIBLE_COLUMNS:
            before = original[column]
            after = edited[column]
            if pd.isna(before) and pd.isna(after):
                continue

            if isinstance(before, pd.Timestamp) and isinstance(after, pd.Timestamp):
                before = before.date()
                after = after.date()

            if before != after:
                row = {
                    "Change Type": "Modified",
                    "Transaction ID": edited.get("Transaction ID"),
                    "Field": column,
                    "Before": before,
                    "After": after,
                }
                if selected:
                    row["Record Key"] = original_key
                diff_rows.append(row)

    for original_key, original in original_map.items():
        if original_key not in edited_map:
            row = {
                "Change Type": "Deleted",
                "Transaction ID": original.get("Transaction ID"),
                "Field": "Row",
                "Before": original[VISIBLE_COLUMNS].to_dict(),
                "After": None,
            }
            if selected:
                row["Record Key"] = original_key
            diff_rows.append(row)

    diff_df = pd.DataFrame(diff_rows)
    if selected:
        diff_df = _add_selection_column(diff_df)
        diff_df = diff_df[["Selected", "Record Key"] + [c for c in diff_df.columns if c not in ("Selected", "Record Key")]]
    return diff_df


def _rows_equal_generic(left, right):
    for column in left.index:
        left_value = left[column]
        right_value = right[column]

        if pd.isna(left_value) and pd.isna(right_value):
            continue

        if isinstance(left_value, pd.Timestamp) and isinstance(right_value, pd.Timestamp):
            if left_value.date() != right_value.date():
                return False
            continue

        if left_value != right_value:
            return False

    return True


def pool_records_for_save(original_df, edited_df):
    records = []
    original_map = {str(index): row for index, row in original_df.iterrows()} if original_df is not None else {}
    edited_map = {str(index): row for index, row in edited_df.iterrows()}

    for original_key in original_map:
        if original_key not in edited_map:
            records.append({"_action": "delete", "original_key": original_key})

    for original_key, edited in edited_df.iterrows():
        original_key = str(original_key)
        if original_key and original_key in original_map and _rows_equal_generic(original_map[original_key], edited):
            continue

        record = edited.to_dict()
        record["original_key"] = original_key
        records.append(record)

    return records


def build_pool_diff(original_df, edited_df, id_label="Record ID", selected=False):
    columns = ["Change Type", id_label, "Field", "Before", "After"]
    if selected:
        columns = ["Selected", "Record Key"] + columns

    if original_df is None or edited_df is None:
        diff_df = pd.DataFrame(columns=columns)
        return _add_selection_column(diff_df) if selected else diff_df

    original_map = {str(index): row for index, row in original_df.iterrows()}
    edited_map = {str(index): row for index, row in edited_df.iterrows()}

    diff_rows = []
    for original_key, edited in edited_df.iterrows():
        original_key = str(original_key)
        if original_key not in original_map:
            row = {
                "Change Type": "Added",
                id_label: original_key,
                "Field": "Row",
                "Before": None,
                "After": edited.to_dict(),
            }
            if selected:
                row["Record Key"] = original_key
            diff_rows.append(row)
            continue

        original = original_map[original_key]
        for column in original_df.columns:
            before = original[column]
            after = edited[column]
            if pd.isna(before) and pd.isna(after):
                continue

            if isinstance(before, pd.Timestamp) and isinstance(after, pd.Timestamp):
                before = before.date()
                after = after.date()

            if before != after:
                row = {
                    "Change Type": "Modified",
                    id_label: original_key,
                    "Field": column,
                    "Before": before,
                    "After": after,
                }
                if selected:
                    row["Record Key"] = original_key
                diff_rows.append(row)

    for original_key, original in original_map.items():
        if original_key not in edited_map:
            row = {
                "Change Type": "Deleted",
                id_label: original_key,
                "Field": "Row",
                "Before": original.to_dict(),
                "After": None,
            }
            if selected:
                row["Record Key"] = original_key
            diff_rows.append(row)

    diff_df = pd.DataFrame(diff_rows)
    if selected:
        diff_df = _add_selection_column(diff_df)
        diff_df = diff_df[["Selected", "Record Key"] + [c for c in diff_df.columns if c not in ("Selected", "Record Key")]]
    return diff_df


def transaction_records_for_save(original_df, edited_df):
    records = []
    original_map = {str(index): row for index, row in original_df.iterrows()} if original_df is not None else {}
    edited_map = {str(index): row for index, row in edited_df.iterrows()}

    for original_key in original_map:
        if original_key not in edited_map:
            records.append({"_action": "delete", "original_key": original_key})

    for original_key, edited in edited_df.iterrows():
        original_key = str(original_key)
        if original_key and original_key in original_map:
            if _rows_equal(original_map[original_key], edited):
                continue

        record = {
            "original_key": original_key,
            "Transaction ID": edited.get("Transaction ID"),
            "Date": edited.get("Date"),
            "Account": edited.get("Account"),
            "Category": edited.get("Category"),
            "Description": edited.get("Description"),
            "Amount": edited.get("Amount"),
            "Balance After": edited.get("Balance After"),
            "Source Sheet": edited.get("Source Sheet"),
            "row_nr": None,
            "account_id": None,
            "category_id": None,
        }
        records.append(record)

    return records
