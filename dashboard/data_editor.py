import pandas as pd
import streamlit as st

from dashboard.sheets import (
    build_pool_diff,
    build_pool_sheet,
    build_transaction_diff,
    build_transaction_sheet,
    pool_records_for_save,
    render_data_sheet,
    render_transaction_sheet,
    transaction_records_for_save,
)


def _fetch_pool_data(queries, pool, effective_start_date, effective_end_date):
    if pool == "Cash":
        rows = queries.get_transactions(
            start_date=effective_start_date,
            end_date=effective_end_date,
            limit=1000,
        )
        return build_transaction_sheet(rows)

    if pool == "Stocks":
        rows = queries.get_stock_positions(
            start_date=effective_start_date,
            end_date=effective_end_date,
        )
        columns = [
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
            "row_nr",
        ]
        visible_columns = columns[:-1]
        return build_pool_sheet(rows, columns, "Position ID", visible_columns)

    if pool == "Goods":
        rows = queries.get_goods_valuations(
            start_date=effective_start_date,
            end_date=effective_end_date,
        )
        columns = [
            "Valuation ID",
            "Valuation Date",
            "Item Name",
            "Purchase Value",
            "Depreciation Input",
            "Value Previous",
            "Value Change",
            "Current Value",
            "Source Sheet",
            "row_nr",
        ]
        visible_columns = columns[:-1]
        return build_pool_sheet(rows, columns, "Valuation ID", visible_columns)

    if pool == "Account Balances":
        rows = queries.get_account_balance_entries(
            start_date=effective_start_date,
            end_date=effective_end_date,
        )
        columns = [
            "Balance ID",
            "Balance Date",
            "Account Name",
            "Balance",
            "Previous Balance",
            "Delta",
            "Entry Type",
            "Source Sheet",
        ]
        return build_pool_sheet(rows, columns, "Balance ID", columns)

    if pool == "Interest":
        rows = queries.get_interest_balance_changes(
            start_date=effective_start_date,
            end_date=effective_end_date,
        )
        columns = [
            "Change ID",
            "Balance Date",
            "Account Name",
            "Balance",
            "Previous Balance",
            "Delta",
            "Source Sheet",
        ]
        return build_pool_sheet(rows, columns, "Change ID", columns)

    if pool == "Categories":
        rows = queries.get_categories()
        columns = [
            "Category ID",
            "Main Category ID",
            "Sub Category ID",
            "Category Name",
            "Category Type",
            "Color Code",
        ]
        visible_columns = [
            "Main Category ID",
            "Sub Category ID",
            "Category Name",
            "Category Type",
            "Color Code",
        ]
        return build_pool_sheet(rows, columns, "Category ID", visible_columns)

    return pd.DataFrame()


def _render_backend_table(queries, pool):
    if pool == "Accounts":
        rows = queries.get_active_account_names()
        df = pd.DataFrame(rows, columns=["Account Name"])
    elif pool == "Main Categories":
        rows = queries.get_main_category_names()
        df = pd.DataFrame(rows, columns=["Main Category"])
    else:
        rows = queries.get_sub_category_names()
        df = pd.DataFrame(rows, columns=["Sub Category"])

    st.subheader(f"{pool} Backend Table")
    st.write(
        "This backend table is shown in Expert mode. Editing is not supported here yet."
    )
    st.dataframe(df, use_container_width=True)


def render_data_editor_sidebar(application_mode="Standard", expert_mode=False):
    st.sidebar.title("Data Filters")
    base_options = ["Cash", "Stocks", "Goods", "Interest", "Account Balances"]
    expert_options = ["Accounts", "Categories", "Main Categories", "Sub Categories"] if expert_mode else []
    pool_options = base_options + expert_options

    current_pool = st.session_state.get("data_pool", base_options[0])
    if current_pool not in pool_options:
        current_pool = base_options[0]

    pool = st.sidebar.radio(
        "Pool",
        pool_options,
        index=pool_options.index(current_pool),
    )

    if st.session_state.get("data_pool") != pool:
        st.session_state.data_pool = pool
        st.session_state.data_original = None
        st.session_state.data_edited = None
        st.session_state.data_preview_requested = False
        st.rerun()

    return pool


def render_data_editor_view(
    queries,
    effective_start_date,
    effective_end_date,
    pool,
    simple_mode=False,
):
    st.header("Data Viewer" if simple_mode else "Data Editor")

    if pool in ["Accounts", "Main Categories", "Sub Categories"]:
        _render_backend_table(queries, pool)
        return

    if simple_mode:
        st.info(
            "Simple mode is enabled. Data Editor should switch to view-only mode; this is a TODO placeholder."
        )

    if not simple_mode:
        if st.button("Load data from database", key="load_data"):
            st.session_state.data_original = None
            st.session_state.data_preview_requested = False

        if st.button("Discard changes and reload", key="discard_data"):
            st.session_state.data_original = None
            st.session_state.data_preview_requested = False

    if st.session_state.data_original is None:
        st.session_state.data_original = _fetch_pool_data(queries, pool, effective_start_date, effective_end_date)
        st.session_state.data_edited = st.session_state.data_original.copy()
        st.session_state.data_preview_requested = False

    if simple_mode:
        st.subheader(f"View-only {pool} Data")
        st.write(
            "TODO: Replace the editable table with a view-only data editor. "
            "For now, this is displayed as a read-only preview."
        )
        st.dataframe(st.session_state.data_original, use_container_width=True)
        return

    st.subheader(f"Editable {pool} Data")
    st.write("Edit data directly in the table, then preview the diff before saving.")

    if pool == "Cash":
        edited_df = render_transaction_sheet(
            st.session_state.data_edited,
            key="data_sheet",
        )
    else:
        edited_df = render_data_sheet(
            st.session_state.data_edited,
            key="data_sheet",
        )

    st.session_state.data_edited = edited_df

    if st.button("Preview save diff", key="preview_save_diff"):
        st.session_state.data_preview_requested = True

    if st.session_state.data_preview_requested:
        if pool == "Cash":
            diff_df = build_transaction_diff(
                st.session_state.data_original,
                st.session_state.data_edited,
            )
        elif pool == "Stocks":
            diff_df = build_pool_diff(
                st.session_state.data_original,
                st.session_state.data_edited,
                id_label="Position ID",
            )
        elif pool == "Goods":
            diff_df = build_pool_diff(
                st.session_state.data_original,
                st.session_state.data_edited,
                id_label="Valuation ID",
            )
        elif pool == "Account Balances":
            diff_df = build_pool_diff(
                st.session_state.data_original,
                st.session_state.data_edited,
                id_label="Balance ID",
            )
        else:
            diff_df = build_pool_diff(
                st.session_state.data_original,
                st.session_state.data_edited,
                id_label="Change ID",
            )

        if diff_df.empty:
            st.info("No differences found between loaded data and edited data.")
        else:
            st.subheader("Pending changes before save")
            st.dataframe(diff_df)
            if st.button("Confirm save to database", key="confirm_save_data"):
                if pool == "Cash":
                    records = transaction_records_for_save(
                        st.session_state.data_original,
                        st.session_state.data_edited,
                    )
                    saved_count = queries.save_transactions(records)
                elif pool == "Stocks":
                    records = pool_records_for_save(
                        st.session_state.data_original,
                        st.session_state.data_edited,
                    )
                    saved_count = queries.save_stock_positions(records)
                elif pool == "Goods":
                    records = pool_records_for_save(
                        st.session_state.data_original,
                        st.session_state.data_edited,
                    )
                    saved_count = queries.save_goods_valuations(records)
                elif pool == "Account Balances":
                    records = pool_records_for_save(
                        st.session_state.data_original,
                        st.session_state.data_edited,
                    )
                    saved_count = queries.save_account_balances(records)
                elif pool == "Categories":
                    records = pool_records_for_save(
                        st.session_state.data_original,
                        st.session_state.data_edited,
                    )
                    saved_count = queries.save_categories(records)
                else:
                    records = pool_records_for_save(
                        st.session_state.data_original,
                        st.session_state.data_edited,
                    )
                    saved_count = queries.save_interest_balance_changes(records)

                st.success(f"Saved {saved_count} records to the database.")
                st.session_state.data_original = None
                st.session_state.data_edited = None
                st.session_state.data_preview_requested = False
