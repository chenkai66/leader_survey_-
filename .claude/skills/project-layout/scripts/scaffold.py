#!/usr/bin/env python3
"""Scaffold a new project following the project-layout standard.

Usage:
    python ~/.claude/skills/project-layout/scripts/scaffold.py <project_path> [--name NAME] [--no-git]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
TEMPLATES = SKILL_DIR / "templates"

# Directory tree to create
DIRS = [
    "data/raw", "data/interim", "data/cleaned", "data/final",
    "specs",
    "code/pipeline", "code/analysis", "code/fillers", "code/validators", "code/lib",
    "results/tables", "results/figures", "results/raw_output",
    "feedback",
    "docs",
    "scripts",
    "tests",
    ".claude/skills",
]


def _render(tpl_name: str, **vars) -> str:
    """Read a template, substitute {VAR} placeholders."""
    text = (TEMPLATES / tpl_name).read_text()
    for k, v in vars.items():
        text = text.replace(f"{{{k}}}", v)
    return text


def _write(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if executable:
        os.chmod(path, 0o755)


def _write_keep(path: Path) -> None:
    (path / ".gitkeep").write_text("")


def scaffold(project_path: Path, name: str, init_git: bool = True) -> None:
    project_path = project_path.expanduser().resolve()
    if project_path.exists() and any(project_path.iterdir()):
        print(f"ERROR: {project_path} exists and is non-empty. Refusing to scaffold.")
        sys.exit(1)
    project_path.mkdir(parents=True, exist_ok=True)
    print(f"Scaffolding {name} at {project_path}")

    # Create directory tree (with .gitkeep so empty dirs persist in git)
    for d in DIRS:
        full = project_path / d
        full.mkdir(parents=True, exist_ok=True)
        _write_keep(full)

    # Top-level files
    _write(project_path / "README.md",  _render("README.md.template", PROJECT_NAME=name))
    _write(project_path / "CLAUDE.md",  _render("CLAUDE.md.template", PROJECT_NAME=name, LOCAL_PATH=str(project_path)))
    _write(project_path / ".gitignore", (TEMPLATES / "gitignore").read_text())
    _write(project_path / "scripts/run_pipeline.sh",
           _render("run_pipeline.sh.template", PROJECT_NAME=name), executable=True)
    _write(project_path / "scripts/validate.sh",
           "#!/usr/bin/env bash\nset -euo pipefail\ncd \"$(dirname \"$0\")/..\"\npython3 code/validators/audit.py\n",
           executable=True)
    _write(project_path / "docs/decision_log.md", (TEMPLATES / "decision_log.md.template").read_text())
    _write(project_path / "docs/methodology.md",  f"# {name} — Methodology\n\n（在这里说明方法论：怎么造数、怎么分析、用了什么模型、为什么）\n")
    _write(project_path / "docs/changelog.md",    "# Changelog\n\n## v0.1.0 (init)\n- Scaffolded from project-layout skill.\n")

    # Specs (skeleton)
    _write(project_path / "specs/data_spec.json",
           json.dumps({
               "n": 1000,
               "columns": [
                   {"name": "x1", "dist": "normal",    "mean": 0, "sd": 1},
                   {"name": "x2", "dist": "lognormal", "mu": 1,   "sigma": 0.5}
               ],
               "correlations": {},
               "constraints":  []
           }, indent=2))
    _write(project_path / "specs/targets.json",
           json.dumps({"description": "目标值（相关、均值、效应量等），用于 validate", "items": {}}, indent=2))
    _write(project_path / "specs/constraints.json",
           json.dumps({"rules": []}, indent=2))
    _write(project_path / "specs/schema.json",
           json.dumps({"description": "列定义：dtype / range / 允许值", "columns": {}}, indent=2))

    # Manifest skeletons
    _write(project_path / "data/_manifest.json",
           json.dumps({"N": None, "generated_at": None, "generator": None, "files": {}}, indent=2))
    _write(project_path / "results/_manifest.json",
           json.dumps({"generated_at": None, "files": {}}, indent=2))

    # Pipeline placeholders
    _write(project_path / "code/pipeline/01_generate.py",
           "\"\"\"Step 01 — generate raw data from specs/data_spec.json.\"\"\"\n"
           "import json\nfrom pathlib import Path\n"
           "# from calibrate import generate_from_spec  # uncomment after pip install / vendor calibrate\n\n"
           "if __name__ == '__main__':\n"
           "    spec = json.load(open('specs/data_spec.json'))\n"
           "    print('TODO: implement step 01 using spec', spec)\n")
    _write(project_path / "code/validators/audit.py",
           "\"\"\"Run all consistency checks; exit 1 on failure.\"\"\"\n"
           "import sys\n# from calibrate import check_referential_integrity, check_aggregate, ...\n\n"
           "def main():\n"
           "    print('TODO: implement audit checks')\n"
           "    return 0\n\n"
           "if __name__ == '__main__':\n"
           "    sys.exit(main())\n")

    # First feedback round folder (empty placeholders)
    fb = project_path / "feedback/round_1"
    fb.mkdir(exist_ok=True)
    (fb / "original").mkdir(exist_ok=True); _write_keep(fb / "original")
    _write(fb / "annotations.md", "# Round 1 annotations\n\n（从客户原文件提取的所有反馈条目）\n")
    _write(fb / "changes.md",     "# Round 1 changes\n\n## Done\n\n## Deferred / not done\n\n## Open\n")

    # tests scaffold
    _write(project_path / "tests/test_data_integrity.py",
           "\"\"\"Assert basic data integrity (rows, columns, no nulls in keys).\"\"\"\n"
           "def test_placeholder():\n    assert True\n")

    # git init (optional)
    if init_git:
        try:
            subprocess.run(["git", "init", "-b", "main"], cwd=project_path, check=True, capture_output=True)
            subprocess.run(["git", "add", "-A"], cwd=project_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"init {name}: scaffold from project-layout"],
                           cwd=project_path, check=True, capture_output=True)
            print("  git initialized + initial commit on main")
        except subprocess.CalledProcessError as e:
            print(f"  git init failed (continuing): {e}")

    print(f"\n✓ done. Project at {project_path}")
    print("\nNext:")
    print(f"  cd {project_path}")
    print("  # edit README.md / CLAUDE.md / specs/data_spec.json")
    print("  # put data in data/raw/")
    print("  # implement code/pipeline/01_generate.py and downstream")
    print("  # ./scripts/run_pipeline.sh && ./scripts/validate.sh")
    print("  # when first ready to deliver: git checkout --orphan delivery → cherry-pick client-facing files → push")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("project_path", help="Where to create the project (absolute or relative)")
    p.add_argument("--name", default=None, help="Project display name (default: dir basename)")
    p.add_argument("--no-git", action="store_true", help="Skip git init")
    a = p.parse_args()
    path = Path(a.project_path)
    name = a.name or path.name
    scaffold(path, name, init_git=not a.no_git)


if __name__ == "__main__":
    main()
