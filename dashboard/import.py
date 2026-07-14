import calendar
import contextlib
import io
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

from src.import_transactions import FinanceImporter


def _save_uploaded_file(uploaded_file):
    suffix = Path(uploaded_file.name).suffix or ".xlsx"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.write(uploaded_file.read())
    temp_file.flush()
    temp_file.close()
    return temp_file.name


def _capture_import_output(func, *args, **kwargs):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        result = func(*args, **kwargs)
    return result, buffer.getvalue()


def render_import_view(db_path: str):
    st.subheader("Excel Import Tool")
    st.write(
        "Upload an Excel workbook, select a sheet, and import the parsed pools into the dashboard database."
    )

    uploaded_file = st.file_uploader(
        "Upload Excel file",
        type=["xlsx", "xls"],
        help="Select the workbook file to import into the finance database.",
    )

    question_text = st.text_area(
        "Questions / notes",
        help="Optional notes or questions for this import action.",
        placeholder="Enter any notes or questions here...",
    )

    if uploaded_file is None:
        return

    if (
        "import_file_name" not in st.session_state
        or st.session_state.import_file_name != uploaded_file.name
    ):
        st.session_state.import_file_path = _save_uploaded_file(uploaded_file)
        st.session_state.import_file_name = uploaded_file.name
        st.session_state.sheets = None
        st.session_state.load_output = None

    importer = FinanceImporter(st.session_state.import_file_path, db_path)

    if st.session_state.sheets is None:
        load_result, load_output = _capture_import_output(importer.load_excel)
        st.session_state.sheets = load_result
        st.session_state.load_output = load_output
    else:
        load_result = st.session_state.sheets
        load_output = st.session_state.load_output

    st.text_area("Import CLI output", load_output, height=180)

    if not load_result:
        return

    sheet_choices = [""] + load_result
    selected_sheet = st.selectbox(
        "Select sheet to import",
        sheet_choices,
        index=0,
        format_func=lambda value: "Select a sheet..." if value == "" else value,
    )

    if selected_sheet:
        importer.sheet_name = selected_sheet
        suggested_date = importer._extract_date_from_sheet()
        sheet_key = selected_sheet.replace(" ", "_").replace("/", "_").replace("\\", "_")
        date_value = st.date_input(
            "Transaction date",
            value=suggested_date or date.today(),
            key=f"import_transaction_date_{sheet_key}",
            help="Date to apply to imported transactions.",
        )

        detected_accounts = set()
        detected_header_account = None
        try:
            raw = importer._load_raw_grid()
            pools = importer._detect_pools()
            if pools.get("cash"):
                cash_data = importer._parse_cash_pool(raw, pools["cash"]["header_row"], pools["cash"]["end_row"])
                if cash_data and cash_data.get("records"):
                    detected_accounts = {
                        record["account_name"]
                        for record in cash_data["records"]
                        if record.get("account_name")
                    }
            if not detected_accounts:
                detected_header_account = importer._detect_account_name()
        except Exception:
            detected_header_account = importer._detect_account_name()

        if detected_accounts:
            st.success(
                "Detected account names: " + ", ".join(sorted(detected_accounts))
            )
        elif detected_header_account:
            st.info(f"Detected account name from sheet header: {detected_header_account}")
        else:
            st.warning(
                "No account names were detected from the selected sheet. "
                "Enter a fallback account name below if needed."
            )
    else:
        date_value = st.date_input(
            "Transaction date",
            value=date.today(),
            help="Date to apply to imported transactions.",
        )

    account_name = st.text_input(
        "Account name",
        value="",
        help="Optional account name to assign imported cash rows if not detected from the workbook.",
    )

    if st.button("Run import"):
        importer.sheet_name = selected_sheet
        if account_name:
            importer.account_name = account_name

        result, import_output = _capture_import_output(
            importer.import_sheet,
            selected_sheet,
            account_name or None,
            date_value,
        )

        if question_text:
            import_output += f"\n\n[QUESTION] {question_text}\n"

        st.text_area("Import log", import_output, height=260)
        st.success("Import completed. See log and result below.")
        st.json(result)
