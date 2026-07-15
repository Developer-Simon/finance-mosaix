from pathlib import Path

import duckdb
import streamlit as st

from src.db_schema import init_database
from dashboard.create_sample_database import seed_sample_data
from dashboard.settings import DEFAULT_SETTINGS, SAMPLE_DATABASE_PATH, save_settings

POOL_OPTIONS = ["Cash", "Stocks", "Goods", "Interest"]


def _resolve_database_path(root_dir: Path, path_value: str, demo_mode: bool = False) -> str:
    if demo_mode:
        selected_path = root_dir / SAMPLE_DATABASE_PATH
    else:
        if not path_value or not path_value.strip():
            path_value = DEFAULT_SETTINGS["database"]["database_path"]

        selected_path = Path(path_value)
        if not selected_path.is_absolute():
            selected_path = root_dir / selected_path

    return str(selected_path.resolve())


def _ensure_database(path: str, demo_mode: bool) -> None:
    conn = init_database(path)
    conn.close()
    if demo_mode:
        conn = duckdb.connect(path)
        try:
            seed_sample_data(conn)
        finally:
            conn.close()


def render_onboarding_view(settings: dict, root_dir: Path) -> None:
    database_settings = settings.setdefault("database", {})
    general_settings = settings.setdefault("general", {})
    current_demo_mode = database_settings.get("demo_mode", DEFAULT_SETTINGS["database"]["demo_mode"])
    current_database_path = database_settings.get("database_path", DEFAULT_SETTINGS["database"]["database_path"])
    current_default_pools = general_settings.get("default_pools", DEFAULT_SETTINGS["general"]["default_pools"])

    st.title("Welcome to Finance Dashboard")
    st.write(
        "Set up your first database connection and choose which pools you want visible by default. "
        "Demo mode creates a pre-populated sample database so you can explore the dashboard immediately."
    )

    demo_mode = st.checkbox(
        "Start in demo mode with sample data",
        value=current_demo_mode,
        key="onboarding_demo_mode",
        help="Use the bundled sample database and explore the dashboard without importing your own data.",
    )

    with st.form("onboarding_form"):
        if demo_mode:
            database_path = st.text_input(
                "Database path",
                value=SAMPLE_DATABASE_PATH,
                key="onboarding_database_path",
                disabled=True,
                help="Demo mode always uses the static sample database path.",
            )
        else:
            database_path = st.text_input(
                "Database path",
                value=current_database_path,
                help="Enter a local DuckDB file path. Relative paths are stored relative to the project root.",
            )

        resolved_database_path = _resolve_database_path(root_dir, database_path, demo_mode=demo_mode)
        st.caption(f"Database will be created at: {resolved_database_path}")

        selected_pools = st.multiselect(
            "Default pools",
            POOL_OPTIONS,
            default=current_default_pools or POOL_OPTIONS,
            help="Choose which pools should be enabled by default in the Charts page.",
        )

        if not selected_pools:
            st.warning("No pools selected. The dashboard will still work, but charts may be limited.")

        submit = st.form_submit_button("Save and continue")

    if submit:
        database_settings["demo_mode"] = bool(demo_mode)
        if not demo_mode:
            database_settings["database_path"] = resolved_database_path
        general_settings["default_pools"] = selected_pools or POOL_OPTIONS
        settings["database"] = database_settings
        settings["general"] = general_settings
        save_settings(settings)

        _ensure_database(resolved_database_path, demo_mode)

        st.session_state["onboarding_completed"] = True
        st.success("Onboarding saved. Starting the dashboard now...")
        st.rerun()
