"""Export [project].dependencies from pyproject.toml as a requirements.txt file."""

import argparse
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PYPROJECT = REPO_ROOT / "pyproject.toml"
DEFAULT_OUT = REPO_ROOT / "electron" / "build" / "requirements.txt"


def render_requirements(pyproject_text: str) -> str:
    data = tomllib.loads(pyproject_text)
    dependencies = data["project"]["dependencies"]
    return "".join(f"{dependency}\n" for dependency in dependencies)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", type=Path, default=DEFAULT_PYPROJECT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    text = args.pyproject.read_text(encoding="utf-8")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_requirements(text), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
