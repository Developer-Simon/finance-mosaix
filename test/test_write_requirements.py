import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "electron" / "scripts" / "write_requirements.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("write_requirements", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_render_requirements_lists_dependencies_in_order():
    module = _load_script()
    text = '[project]\nname = "x"\ndependencies = ["a>=1", "b<2"]\n'
    assert module.render_requirements(text) == "a>=1\nb<2\n"


def test_real_pyproject_contains_streamlit():
    module = _load_script()
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    output = module.render_requirements(text)
    assert "numpy>=1.25,<3" in output
    assert "streamlit>=1.20,<2.0" in output
