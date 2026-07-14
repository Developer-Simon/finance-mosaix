import copy
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

try:
    from src.db_migrate import get_db_version, CURRENT_DB_VERSION
except ImportError:
    from db_migrate import get_db_version, CURRENT_DB_VERSION

SETTINGS_FILE_NAME = "settings.json"
PROJECT_VERSION = "0.1"

DEFAULT_SETTINGS = {
    "home": {
        "show_chart_subheaders": True,
        "page_title": "Home",
    },
    "charts": {
        "default_chart": "Timeline",
        "default_filter_mode": "Full database",
        "show_underlying_data": False,
        "use_legacy_pyplots": False,
    },
    "dashboard": {
        "application_mode": "Standard",
        "notification_mode": "Home only",
        "ignored_notifications": [],
    },
}

APPLICATION_MODE_OPTIONS = [
    "Standard",
    "Simple",
    "Expert",
]

CHART_OPTIONS = [
    "Timeline",
    "Spending",
    "Balances",
    "Income vs Expenses",
    "Transaction Frequency",
    "Average Transaction",
    "Asset Allocation Trend",
    "Cash Flow Trend",
    "Category Drill-down",
    "Account Balance History",
    "Stock Portfolio Performance",
    "Goods Valuation Change",
    "Interest Growth",
    "Stock Positions",
    "Goods Valuation",
    "Balance with Delta",
]

FILTER_OPTIONS = [
    "Full database",
    "Month range",
    "Exact dates",
]


def get_settings_file_path() -> Path:
    settings_path = Path(__file__).resolve().parent / SETTINGS_FILE_NAME
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    return settings_path


def _normalize_settings(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return copy.deepcopy(DEFAULT_SETTINGS)

    # Support legacy flat settings structure
    normalized = copy.deepcopy(DEFAULT_SETTINGS)

    if "home" in raw and isinstance(raw["home"], dict):
        normalized["home"].update(raw["home"])
    else:
        if "home_show_chart_subheaders" in raw:
            normalized["home"]["show_chart_subheaders"] = raw["home_show_chart_subheaders"]
        if "home_page_title" in raw:
            normalized["home"]["page_title"] = raw["home_page_title"]

    if "charts" in raw and isinstance(raw["charts"], dict):
        normalized["charts"].update(raw["charts"])
    else:
        if "default_chart" in raw:
            normalized["charts"]["default_chart"] = raw["default_chart"]
        if "default_filter_mode" in raw:
            normalized["charts"]["default_filter_mode"] = raw["default_filter_mode"]
        if "show_underlying_data" in raw:
            normalized["charts"]["show_underlying_data"] = raw["show_underlying_data"]
        if "use_legacy_pyplots" in raw:
            normalized["charts"]["use_legacy_pyplots"] = raw["use_legacy_pyplots"]

    if "dashboard" in raw and isinstance(raw["dashboard"], dict):
        normalized["dashboard"].update(raw["dashboard"])
    else:
        if "application_mode" in raw:
            normalized["dashboard"]["application_mode"] = raw["application_mode"]

    if normalized["dashboard"]["application_mode"] == "Export":
        normalized["dashboard"]["application_mode"] = "Expert"

    return normalized


def load_settings() -> dict:
    settings_path = get_settings_file_path()
    if not settings_path.exists():
        return copy.deepcopy(DEFAULT_SETTINGS)

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
        return _normalize_settings(raw)
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    settings_path = get_settings_file_path()
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def get_database_version(queries) -> str:
    if queries is None:
        return CURRENT_DB_VERSION

    try:
        return get_db_version(queries.conn)
    except Exception:
        return CURRENT_DB_VERSION


def render_settings_view(db_path: str, queries, expert_mode: bool = False):
    settings = load_settings()

    st.header("Settings")
    st.write(
        "Use this page to persist dashboard defaults and view project metadata. "
        "The selected values are stored in a JSON file and preserved across app restarts."
    )

    with st.form("dashboard_settings_form"):
        st.subheader("Home Page Settings")
        home_show_chart_subheaders = st.checkbox(
            "Show chart subheaders on Home screen",
            value=settings["home"].get("show_chart_subheaders", DEFAULT_SETTINGS["home"]["show_chart_subheaders"]),
        )
        home_page_title = st.text_input(
            "Home screen title",
            value=settings["home"].get("page_title", DEFAULT_SETTINGS["home"]["page_title"]),
            help="If left empty, the Home page title will be hidden.",
        )

        st.subheader("Charts Page Settings")
        selected_chart = st.selectbox(
            "Default chart for the Charts page",
            CHART_OPTIONS,
            index=CHART_OPTIONS.index(settings["charts"].get("default_chart", DEFAULT_SETTINGS["charts"]["default_chart"]))
            if settings["charts"].get("default_chart") in CHART_OPTIONS
            else 0,
        )
        selected_filter = st.selectbox(
            "Default filter mode",
            FILTER_OPTIONS,
            index=FILTER_OPTIONS.index(settings["charts"].get("default_filter_mode", DEFAULT_SETTINGS["charts"]["default_filter_mode"]))
            if settings["charts"].get("default_filter_mode") in FILTER_OPTIONS
            else 0,
        )
        show_data_default = st.checkbox(
            "Show underlying chart data by default",
            value=settings["charts"].get("show_underlying_data", DEFAULT_SETTINGS["charts"]["show_underlying_data"]),
        )
        enable_legacy_pyplots = st.checkbox(
            "Enable legacy Pyplot page",
            value=settings["charts"].get("use_legacy_pyplots", DEFAULT_SETTINGS["charts"]["use_legacy_pyplots"]),
            help="Show the legacy Pyplot visualization page in the dashboard navigation.",
        )

        st.subheader("General settings")
        selected_app_mode = st.selectbox(
            "Application mode",
            APPLICATION_MODE_OPTIONS,
            index=APPLICATION_MODE_OPTIONS.index(
                settings["dashboard"].get("application_mode", DEFAULT_SETTINGS["dashboard"]["application_mode"])
            )
            if settings["dashboard"].get("application_mode") in APPLICATION_MODE_OPTIONS
            else 0,
            help="Choose the dashboard mode. Simple mode reduces navigation and switches the editor into a view-only mode.",
        )

        notification_mode = st.selectbox(
            "Balance notification visibility",
            ["Home only", "Every page", "Hide"],
            index=["Home only", "Every page", "Hide"].index(
                settings["dashboard"].get("notification_mode", DEFAULT_SETTINGS["dashboard"]["notification_mode"])
            ) if settings["dashboard"].get("notification_mode") in ["Home only", "Every page", "Hide"] else 0,
            help="Choose where the calculated balance notification appears in the dashboard.",
        )

        if st.form_submit_button("Save settings"):
            settings["home"] = {
                "show_chart_subheaders": home_show_chart_subheaders,
                "page_title": home_page_title,
            }
            settings["charts"] = {
                "default_chart": selected_chart,
                "default_filter_mode": selected_filter,
                "show_underlying_data": show_data_default,
                "use_legacy_pyplots": enable_legacy_pyplots,
            }
            settings["dashboard"] = {
                "application_mode": selected_app_mode,
                "notification_mode": notification_mode,
                "ignored_notifications": settings["dashboard"].get("ignored_notifications", []),
            }
            save_settings(settings)
            st.success("Dashboard settings saved.")
            st.rerun()

    st.markdown("---")
    st.subheader("Project and database information")
    st.write("These values are derived from the project state and the active database.")
    st.write("**Project version:**", PROJECT_VERSION)
    st.write("**Database version:**", get_database_version(queries))
    st.write("**Database path:**", db_path)
    st.write("**Settings file:**", str(get_settings_file_path()))
    if get_settings_file_path().exists():
        st.write(
            "**Last saved:**",
            datetime.fromtimestamp(get_settings_file_path().stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        )

    st.markdown("---")
    st.subheader("Ignored notifications")
    ignored_notifications = settings["dashboard"].get("ignored_notifications", [])
    if ignored_notifications:
        st.write(
            "The following notification codes are currently ignored:",
            ", ".join(ignored_notifications),
        )
    else:
        st.write("No ignored notifications are currently ignored.")

    if st.button("Erase all ignored notifications", key="erase_ignored_notifications"):
        settings["dashboard"]["ignored_notifications"] = []
        save_settings(settings)
        st.success("All ignored notifications have been cleared.")
        st.rerun()

    if expert_mode:
        st.markdown("---")
        st.subheader("Current persistent settings")
        st.json(settings)
