import copy
import json
import tomllib
from datetime import datetime
from pathlib import Path

import streamlit as st

try:
    from src.db_migrate import get_db_version, CURRENT_DB_VERSION
except ImportError:
    from db_migrate import get_db_version, CURRENT_DB_VERSION

SETTINGS_FILE_NAME = "settings.json"
SAMPLE_DATABASE_PATH = "finance_sample.duckdb"


def get_project_version() -> str:
    config_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    if not config_path.exists():
        return "0.0.0"

    with config_path.open("rb") as handle:
        config = tomllib.load(handle)

    return str(config.get("project", {}).get("version", "0.0.0"))


PROJECT_VERSION = get_project_version()

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
    "general": {
        "application_mode": "Standard",
        "notification_mode": "Home only",
        "ignored_notifications": [],
        "default_pools": ["Cash", "Stocks", "Goods", "Interest"],
    },
    "database": {
        "database_path": "finance.duckdb",
        "demo_mode": False,
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

    if "general" in raw and isinstance(raw["general"], dict):
        normalized["general"].update(raw["general"])
    else:
        if "application_mode" in raw:
            normalized["general"]["application_mode"] = raw["application_mode"]
        if "default_pools" in raw:
            normalized["general"]["default_pools"] = raw["default_pools"]
        if "notification_mode" in raw:
            normalized["general"]["notification_mode"] = raw["notification_mode"]
        if "ignored_notifications" in raw:
            normalized["general"]["ignored_notifications"] = raw["ignored_notifications"]

    if "database" in raw and isinstance(raw["database"], dict):
        normalized["database"].update(raw["database"])
    else:
        if "database_path" in raw:
            normalized["database"]["database_path"] = raw["database_path"]
        if "demo_mode" in raw:
            normalized["database"]["demo_mode"] = raw["demo_mode"]

    if "dashboard" in raw and isinstance(raw["dashboard"], dict):
        normalized["general"]["application_mode"] = raw["dashboard"].get(
            "application_mode",
            normalized["general"]["application_mode"],
        )
        normalized["general"]["notification_mode"] = raw["dashboard"].get(
            "notification_mode",
            normalized["general"]["notification_mode"],
        )
        normalized["general"]["ignored_notifications"] = raw["dashboard"].get(
            "ignored_notifications",
            normalized["general"]["ignored_notifications"],
        )
        normalized["general"]["default_pools"] = raw["dashboard"].get(
            "default_pools",
            normalized["general"]["default_pools"],
        )
        normalized["database"]["database_path"] = raw["dashboard"].get(
            "database_path",
            normalized["database"]["database_path"],
        )
        normalized["database"]["demo_mode"] = raw["dashboard"].get(
            "demo_mode",
            normalized["database"]["demo_mode"],
        )

    if normalized["general"]["application_mode"] == "Export":
        normalized["general"]["application_mode"] = "Expert"

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

    saved_database_path = settings["database"].get("database_path", DEFAULT_SETTINGS["database"]["database_path"])
    saved_demo_mode = settings["database"].get("demo_mode", DEFAULT_SETTINGS["database"]["demo_mode"])

    if "settings_demo_mode" not in st.session_state:
        st.session_state["settings_demo_mode"] = saved_demo_mode
    if "settings_demo_mode_prev" not in st.session_state:
        st.session_state["settings_demo_mode_prev"] = saved_demo_mode
    if "settings_database_path" not in st.session_state:
        st.session_state["settings_database_path"] = saved_database_path
    if "settings_database_path_before_demo" not in st.session_state:
        st.session_state["settings_database_path_before_demo"] = saved_database_path

    if st.session_state["settings_demo_mode"] and not st.session_state["settings_demo_mode_prev"]:
        st.session_state["settings_database_path_before_demo"] = st.session_state["settings_database_path"]
    elif not st.session_state["settings_demo_mode"] and st.session_state["settings_demo_mode_prev"]:
        st.session_state["settings_database_path"] = st.session_state["settings_database_path_before_demo"]

    st.session_state["settings_demo_mode_prev"] = st.session_state["settings_demo_mode"]
    database_path = st.session_state["settings_database_path"]

    st.session_state.setdefault("settings_home_expanded", True)
    st.session_state.setdefault("settings_charts_expanded", True)
    st.session_state.setdefault("settings_general_expanded", True)
    st.session_state.setdefault("settings_database_expanded", True)

    with st.expander(
        "Home Page Settings",
        expanded=st.session_state["settings_home_expanded"],
        key="settings_home_expander",
    ):
        home_show_chart_subheaders = st.checkbox(
            "Show chart subheaders on Home screen",
            value=settings["home"].get("show_chart_subheaders", DEFAULT_SETTINGS["home"]["show_chart_subheaders"]),
        )
        home_page_title = st.text_input(
            "Home screen title",
            value=settings["home"].get("page_title", DEFAULT_SETTINGS["home"]["page_title"]),
            help="If left empty, the Home page title will be hidden.",
        )

    with st.expander(
        "Charts Page Settings",
        expanded=st.session_state["settings_charts_expanded"],
        key="settings_charts_expander",
    ):
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

    with st.expander(
        "General settings",
        expanded=st.session_state["settings_general_expanded"],
        key="settings_general_expander",
    ):
        selected_app_mode = st.selectbox(
            "Application mode",
            APPLICATION_MODE_OPTIONS,
            index=APPLICATION_MODE_OPTIONS.index(
                settings["general"].get("application_mode", DEFAULT_SETTINGS["general"]["application_mode"])
            )
            if settings["general"].get("application_mode") in APPLICATION_MODE_OPTIONS
            else 0,
            help="Choose the dashboard mode. Simple mode reduces navigation and switches the editor into a view-only mode.",
        )

        notification_mode = st.selectbox(
            "Balance notification visibility",
            ["Home only", "Every page", "Hide"],
            index=["Home only", "Every page", "Hide"].index(
                settings["general"].get("notification_mode", DEFAULT_SETTINGS["general"]["notification_mode"])
            ) if settings["general"].get("notification_mode") in ["Home only", "Every page", "Hide"] else 0,
            help="Choose where the calculated balance notification appears in the dashboard.",
        )

        ignored_notifications = settings["general"].get("ignored_notifications", [])
        ignored_notification_selection = st.multiselect(
            "Ignored notifications",
            ignored_notifications,
            default=ignored_notifications,
            help="Select ignored notifications to keep. Clear all selections to remove every ignored notification.",
        )

    with st.expander(
        "Database settings",
        expanded=st.session_state["settings_database_expanded"],
        key="settings_database_expander",
    ):
        start_in_demo_mode = st.checkbox(
            "Start in demo mode with sample data",
            value=st.session_state["settings_demo_mode"],
            key="settings_demo_mode",
            help="When enabled, the dashboard will use the sample database at the selected path.",
        )

        if start_in_demo_mode and not st.session_state.get("settings_demo_mode_prev", False):
            st.session_state["settings_database_path_before_demo"] = st.session_state["settings_database_path"]
        if not start_in_demo_mode and st.session_state.get("settings_demo_mode_prev", False):
            st.session_state["settings_database_path"] = st.session_state.get(
                "settings_database_path_before_demo",
                saved_database_path,
            )

        if start_in_demo_mode:
            st.text_input(
                "Database path",
                value=SAMPLE_DATABASE_PATH,
                key="settings_database_path_demo",
                disabled=True,
                help="Demo mode always uses the static sample database path.",
            )
        else:
            database_path = st.text_input(
                "Database path",
                value=st.session_state["settings_database_path"],
                key="settings_database_path",
                help="Local DuckDB file path for the active database. Relative paths are resolved from the project root.",
            )

        st.session_state["settings_demo_mode_prev"] = start_in_demo_mode

        default_pools = st.multiselect(
            "Default pools",
            ["Cash", "Stocks", "Goods", "Interest"],
            default=settings["general"].get("default_pools", DEFAULT_SETTINGS["general"]["default_pools"]),
            help="Pools selected here will be enabled by default in the Charts page.",
        )

    if st.button("Save settings", key="save_dashboard_settings"):
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
        settings["general"] = {
            "application_mode": selected_app_mode,
            "notification_mode": notification_mode,
            "default_pools": default_pools or DEFAULT_SETTINGS["general"]["default_pools"],
            "ignored_notifications": ignored_notification_selection,
        }
        settings["database"] = {
            "demo_mode": start_in_demo_mode,
            "database_path": DEFAULT_SETTINGS["database"]["database_path"] if start_in_demo_mode else database_path,
        }
        save_settings(settings)
        st.rerun()
        st.success("Dashboard settings saved.")

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

    if expert_mode:
        st.markdown("---")
        st.subheader("Current persistent settings")
        st.json(settings)
