import datetime
import pandas as pd
import streamlit as st

from dashboard.sheets import (
    build_pool_diff,
    build_pool_sheet,
    build_transaction_diff,
    build_transaction_preview_sheet,
)


def _build_merge_preview_diff(queries, pool, merge_type, source_value, target_value):
    if pool == "Cash":
        if merge_type == "Account":
            rows = queries.get_transactions_by_account_name(source_value)
        elif merge_type == "Category":
            rows = queries.get_transactions_by_category_name(source_value)
        else:
            rows = queries.get_transactions_by_date(source_value)

        original_df = build_transaction_preview_sheet(rows)
        if original_df.empty:
            return original_df

        modified_df = original_df.copy()
        if merge_type == "Account":
            modified_df["Account"] = target_value
        elif merge_type == "Category":
            modified_df["Category"] = target_value
        else:
            modified_df["Date"] = target_value

        return build_transaction_diff(original_df, modified_df, selected=True)

    if pool == "Stocks":
        if merge_type == "Name":
            rows = queries.get_stock_positions_by_name(source_value)
        elif merge_type == "Ticker":
            rows = queries.get_stock_positions_by_ticker(source_value)
        else:
            rows = queries.get_stock_positions_by_snapshot_date(source_value)

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
        visible_columns = columns[:-2]
        original_df = build_pool_sheet(rows, columns, "Position ID", visible_columns)
        if original_df.empty:
            return original_df

        modified_df = original_df.copy()
        if merge_type == "Name":
            modified_df["Name"] = target_value
        elif merge_type == "Ticker":
            modified_df["Ticker"] = target_value
        else:
            modified_df["Snapshot Date"] = target_value

        return build_pool_diff(original_df, modified_df, id_label="Position ID", selected=True)

    if pool == "Goods":
        if merge_type == "Item Name":
            rows = queries.get_goods_valuations_by_item_name(source_value)
        elif merge_type == "Valuation Date":
            rows = queries.get_goods_valuations_by_valuation_date(source_value)
        else:
            preview = queries.preview_goods_normalization(item_name=source_value or None)
            rows = preview["original_rows"]
            normalized = preview["normalized_rows"]
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
            visible_columns = columns[:-2]
            original_df = build_pool_sheet(rows, columns, "Valuation ID", visible_columns)
            normalized_df = build_pool_sheet(normalized, columns, "Valuation ID", visible_columns)
            if original_df.empty:
                return original_df
            return build_pool_diff(original_df, normalized_df, id_label="Valuation ID", selected=True)

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
        visible_columns = columns[:-2]
        original_df = build_pool_sheet(rows, columns, "Valuation ID", visible_columns)
        if original_df.empty:
            return original_df

        modified_df = original_df.copy()
        if merge_type == "Item Name":
            modified_df["Item Name"] = target_value
        else:
            modified_df["Valuation Date"] = target_value

        return build_pool_diff(original_df, modified_df, id_label="Valuation ID", selected=True)

    if pool == "Account Balances":
        if merge_type == "Account Name":
            rows = queries.get_account_balance_entries_by_account_name(source_value)
        else:
            rows = queries.get_account_balance_entries_by_balance_date(source_value)

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
        visible_columns = columns
        original_df = build_pool_sheet(rows, columns, "Balance ID", visible_columns)
        if original_df.empty:
            return original_df

        modified_df = original_df.copy()
        if merge_type == "Account Name":
            modified_df["Account Name"] = target_value
        else:
            modified_df["Balance Date"] = target_value

        return build_pool_diff(original_df, modified_df, id_label="Balance ID", selected=True)

    if pool == "Interest":
        if merge_type == "Account Name":
            rows = queries.get_interest_balance_changes_by_account_name(source_value)
        else:
            rows = queries.get_interest_balance_changes_by_balance_date(source_value)

        columns = [
            "Change ID",
            "Balance Date",
            "Account Name",
            "Balance",
            "Previous Balance",
            "Delta",
            "Source Sheet",
        ]
        visible_columns = columns
        original_df = build_pool_sheet(rows, columns, "Change ID", visible_columns)
        if original_df.empty:
            return original_df

        modified_df = original_df.copy()
        if merge_type == "Account Name":
            modified_df["Account Name"] = target_value
        else:
            modified_df["Balance Date"] = target_value

        return build_pool_diff(original_df, modified_df, id_label="Change ID", selected=True)

    return pd.DataFrame()


def render_data_organizer_view(queries):
    st.header("Data Organizer")
    st.sidebar.title("Data Organizer")

    pool = st.sidebar.radio(
        "Pool",
        ["Cash", "Stocks", "Goods", "Interest", "Account Balances"],
        index=0,
    )

    if pool == "Cash":
        merge_type = st.sidebar.radio(
            "Organizer type",
            ["Account", "Category", "Date"],
            index=0,
        )
    elif pool == "Stocks":
        merge_type = st.sidebar.radio(
            "Organizer type",
            ["Name", "Ticker", "Snapshot Date"],
            index=0,
        )
    elif pool == "Goods":
        merge_type = st.sidebar.radio(
            "Organizer type",
            ["Item Name", "Valuation Date", "Normalize Derived Values"],
            index=0,
        )
    elif pool == "Account Balances":
        merge_type = st.sidebar.radio(
            "Organizer type",
            ["Account Name", "Balance Date", "Calculate from Cash"],
            index=0,
        )
    else:
        merge_type = st.sidebar.radio(
            "Organizer type",
            ["Account Name", "Balance Date"],
            index=0,
        )

    def _merge_result(message, success=True):
        if success:
            st.success(message)
        else:
            st.error(message)

    if pool == "Account Balances" and merge_type == "Calculate from Cash":
        st.subheader("Calculate Account Balance from Cash Transactions")
        account_name = st.selectbox(
            "Account Name",
            [""] + queries.get_active_account_names(),
            index=0,
        )

        col_a, col_b = st.columns(2)
        with col_a:
            start_date = st.date_input(
                "Start Date",
                value=st.session_state.get("balance_start_date", datetime.date.today() - datetime.timedelta(days=30)),
            )
        with col_b:
            end_date = st.date_input(
                "End Date",
                value=st.session_state.get("balance_end_date", datetime.date.today()),
            )

        if start_date > end_date:
            st.error("Start Date must be before or equal to End Date.")

        if st.button("Preview calculated account balance range", key="preview_calculated_account_balance"):
            if not account_name:
                st.error("Choose an account to calculate.")
                st.session_state["calculate_cash_preview_requested"] = False
            elif start_date > end_date:
                st.error("Choose a valid date range.")
                st.session_state["calculate_cash_preview_requested"] = False
            else:
                st.session_state["calculate_cash_preview_requested"] = True
                st.session_state["balance_start_date"] = start_date
                st.session_state["balance_end_date"] = end_date

        preview_id = f"{pool}|{merge_type}|{account_name}|{start_date}|{end_date}"
        if st.session_state.get("calculate_cash_preview_id") != preview_id:
            st.session_state["calculate_cash_preview_requested"] = False
            st.session_state["calculate_cash_preview_result"] = None
            st.session_state["calculate_cash_preview_id"] = preview_id

        if st.session_state.get("calculate_cash_preview_requested", False):
            if not account_name:
                st.info("Choose an account and preview again.")
            elif start_date > end_date:
                st.info("Choose a valid date range and preview again.")
            else:
                preview_result = queries.preview_account_balance_snapshots(account_name, start_date, end_date)
                st.session_state["calculate_cash_preview_result"] = preview_result
                st.session_state["calculate_cash_preview_requested"] = False

        preview_result = st.session_state.get("calculate_cash_preview_result")
        if preview_result is not None:
            st.write("### Preview")
            preview_df = pd.DataFrame(preview_result)
            preview_df = preview_df[
                ["balance_date", "account_name", "previous_balance", "delta", "balance", "entry_type", "source_sheet", "calculated"]
            ]
            preview_df = preview_df.rename(
                columns={
                    "balance_date": "Balance Date",
                    "account_name": "Account Name",
                    "previous_balance": "Previous Balance",
                    "delta": "Delta",
                    "balance": "Calculated Balance",
                    "entry_type": "Entry Type",
                    "source_sheet": "Source Sheet",
                    "calculated": "Calculated",
                }
            )
            st.dataframe(preview_df, use_container_width=True)

        if st.button("Create calculated account balances" if start_date != end_date else "Create calculated account balance"):
            if not account_name:
                st.error("Choose an account to calculate.")
            elif start_date > end_date:
                st.error("Choose a valid date range.")
            else:
                try:
                    result = queries.create_account_balance_snapshots(account_name, start_date, end_date)
                    st.success(
                        f"Created {result['rows_created']} calculated account balance snapshot(s) for {result['account_name']} from {result['start_date']} to {result['end_date']}."
                    )
                    st.json(result)
                except Exception as exc:
                    st.error(str(exc))
        return

    if merge_type in ("Account", "Category", "Name", "Ticker", "Item Name", "Account Name"):
        item_label = merge_type

        if pool == "Cash":
            existing_names = (
                queries.get_active_account_names()
                if merge_type == "Account"
                else queries.get_category_names()
            )
        elif pool == "Stocks":
            existing_names = (
                queries.get_stock_names()
                if merge_type == "Name"
                else queries.get_stock_tickers()
            )
        elif pool == "Goods":
            existing_names = queries.get_goods_item_names()
        elif pool == "Account Balances":
            existing_names = queries.get_account_balance_names()
        else:
            existing_names = queries.get_interest_account_names()

        if not existing_names:
            st.info(f"No {item_label.lower()}s are available to merge.")
            return

        source_name = st.selectbox(
            f"Source {item_label}",
            [""] + existing_names,
            index=0,
            help=f"Select the existing {item_label.lower()} to merge from.",
        )

        st.write("---")
        st.write("Choose an existing target or enter a new one.")

        target_existing = st.selectbox(
            f"Target {item_label} (existing)",
            [""] + existing_names,
            index=0,
            help=f"Select an existing {item_label.lower()} to merge into.",
        )
        target_custom = st.text_input(
            f"Target {item_label} (new)",
            value="",
            help=f"Enter a new target {item_label.lower()} name to create.",
        )

        target_name = target_custom.strip() or target_existing

        if st.button("Preview changes", key="preview_merge_diff"):
            if not source_name:
                _merge_result(f"Please select a source {item_label.lower()}.", success=False)
                st.session_state["merge_preview_requested"] = False
            elif not target_name:
                _merge_result(f"Please select or enter a target {item_label.lower()}.", success=False)
                st.session_state["merge_preview_requested"] = False
            elif source_name == target_name:
                _merge_result("Source and target must differ.", success=False)
                st.session_state["merge_preview_requested"] = False
            else:
                st.session_state["merge_preview_requested"] = True

        preview_id = f"{pool}|{merge_type}|{source_name}|{target_name}"
        if st.session_state.get("merge_preview_id") != preview_id:
            st.session_state["merge_preview_requested"] = False
            st.session_state["merge_preview_df"] = None
            st.session_state["merge_preview_id"] = preview_id

        if st.session_state.get("merge_preview_requested", False):
            if not source_name or not target_name or source_name == target_name:
                st.info("Update the source and target selection and preview again.")
            else:
                diff_df = _build_merge_preview_diff(queries, pool, merge_type, source_name, target_name)
                if diff_df.empty:
                    st.info("No records will change for this organization.")
                else:
                    st.subheader("Organization preview diff")
                    merge_preview = st.data_editor(
                        diff_df,
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "Selected": st.column_config.CheckboxColumn(
                                "Selected",
                                default=True,
                            ),
                        },
                        key="merge_preview_diff",
                    )
                    st.session_state["merge_preview_df"] = merge_preview

        if st.button("Apply organization"):
            if not source_name:
                _merge_result(f"Please select a source {item_label.lower()}.", success=False)
            elif not target_name:
                _merge_result(f"Please select or enter a target {item_label.lower()}.", success=False)
            elif source_name == target_name:
                _merge_result("Source and target must differ.", success=False)
            else:
                selected_keys = None
                preview_df = st.session_state.get("merge_preview_df")
                if preview_df is not None and "Selected" in preview_df.columns:
                    selected_keys = preview_df.loc[preview_df["Selected"] == True, "Record Key"].astype(str).tolist()
                    selected_keys = list(dict.fromkeys(selected_keys))
                    if not selected_keys:
                        _merge_result("No rows selected for merge.", success=False)
                        selected_keys = None
                try:
                    if pool == "Cash":
                        if merge_type == "Account":
                            result = queries.merge_accounts(source_name, target_name, selected_keys=selected_keys)
                        else:
                            result = queries.merge_categories(source_name, target_name, selected_keys=selected_keys)
                        description = f"Merged {item_label.lower()} '{result['source']}' into '{result['target']}' and updated {result['rows_updated']} transaction rows."
                    elif pool == "Stocks":
                        if merge_type == "Name":
                            result = queries.merge_stock_positions_by_name(source_name, target_name, selected_position_ids=selected_keys)
                        else:
                            result = queries.merge_stock_positions_by_ticker(source_name, target_name, selected_position_ids=selected_keys)
                        description = f"Merged stock positions {item_label.lower()} '{result['source']}' into '{result['target']}' and updated {result['rows_updated']} rows."
                    elif pool == "Goods":
                        result = queries.merge_goods_valuations_by_item_name(source_name, target_name, selected_valuation_ids=selected_keys)
                        description = f"Merged goods valuations item name '{result['source']}' into '{result['target']}' and updated {result['rows_updated']} rows."
                    elif pool == "Account Balances":
                        result = queries.merge_account_balance_names(source_name, target_name, selected_balance_ids=selected_keys)
                        description = f"Merged account balance account '{result['source']}' into '{result['target']}' and updated {result['rows_updated']} rows."
                    else:
                        result = queries.merge_interest_account_names(source_name, target_name, selected_change_ids=selected_keys)
                        description = f"Merged interest account '{result['source']}' into '{result['target']}' and updated {result['rows_updated']} rows."

                    if selected_keys is not None:
                        description += " (selected rows only)"
                    _merge_result(description)
                except Exception as exc:
                    _merge_result(str(exc), success=False)

    elif pool == "Goods" and merge_type == "Normalize Derived Values":
        item_name = st.selectbox(
            "Item Name (optional)",
            [""] + queries.get_goods_item_names(),
            index=0,
            help="Optional item filter for goods normalization. Leave empty to normalize all goods.",
        )

        if st.button("Preview normalization diff", key="preview_normalization_diff"):
            st.session_state["merge_preview_requested"] = True

        preview_id = f"{pool}|{merge_type}|{item_name}"
        if st.session_state.get("merge_preview_id") != preview_id:
            st.session_state["merge_preview_requested"] = False
            st.session_state["merge_preview_df"] = None
            st.session_state["merge_preview_id"] = preview_id

        if st.session_state.get("merge_preview_requested", False):
            diff_df = _build_merge_preview_diff(queries, pool, merge_type, item_name, None)
            if diff_df.empty:
                st.info("No derived-value changes detected for the selected goods rows.")
            else:
                st.subheader("Normalization preview diff")
                st.dataframe(diff_df)

        if st.button("Apply normalization", key="apply_normalization"):
            try:
                result = queries.normalize_goods_valuations(item_name=item_name or None, what_if=False)
                _merge_result(
                    f"Applied normalization to {result['rows_changed']} rows of {result['rows_processed']} processed goods rows."
                )
            except Exception as exc:
                _merge_result(str(exc), success=False)
    else:
        source_date = st.date_input("Source date")
        target_date = st.date_input("Target date")

        if st.button("Preview changes", key="preview_date_merge_diff"):
            if source_date == target_date:
                _merge_result("Source and target dates must differ.", success=False)
                st.session_state["merge_preview_requested"] = False
            else:
                st.session_state["merge_preview_requested"] = True

        if st.session_state.get("merge_preview_requested", False):
            if source_date == target_date:
                st.info("Update the source and target dates and preview again.")
            else:
                diff_df = _build_merge_preview_diff(queries, pool, merge_type, source_date, target_date)
                if diff_df.empty:
                    st.info("No transactions will change for this organization.")
                else:
                    st.subheader("Organization preview diff")
                    st.dataframe(diff_df)

        if st.button("Apply organization"):
            try:
                if pool == "Cash":
                    result = queries.merge_transaction_dates(source_date, target_date)
                    description = f"Merged transactions from {result['source_date']} into {result['target_date']} ({result['rows_updated']} rows updated)."
                elif pool == "Stocks":
                    result = queries.merge_stock_positions_by_snapshot_date(source_date, target_date)
                    description = f"Merged stock snapshots from {result['source_date']} into {result['target_date']} ({result['rows_updated']} rows updated)."
                elif pool == "Goods":
                    result = queries.merge_goods_valuations_by_valuation_date(source_date, target_date)
                    description = f"Merged goods valuations from {result['source_date']} into {result['target_date']} ({result['rows_updated']} rows updated)."
                elif pool == "Account Balances":
                    result = queries.merge_account_balance_dates(source_date, target_date)
                    description = f"Merged account balances from {result['source_date']} into {result['target_date']} ({result['rows_updated']} rows updated)."
                else:
                    result = queries.merge_interest_balance_dates(source_date, target_date)
                    description = f"Merged interest balances from {result['source_date']} into {result['target_date']} ({result['rows_updated']} rows updated)."

                _merge_result(description)
            except Exception as exc:
                _merge_result(str(exc), success=False)
