"""Rebuild every derived Seattle Matcha Analytics output in dependency order."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    "build_shops_master.py",
    "build_menu_dataset.py",
    "build_analytics_datasets.py",
    "build_sqlite_database.py",
    "run_sql_analysis.py",
    "build_tableau_sources.py",
]


def main() -> None:
    for index, script_name in enumerate(STEPS, start=1):
        print(f"\n[{index}/{len(STEPS)}] Running {script_name}")
        subprocess.run(
            [sys.executable, str(ROOT / "src" / script_name)],
            cwd=ROOT,
            check=True,
        )
    print("\nPipeline complete: processed data, SQLite, SQL reports, and Tableau sources are current.")


if __name__ == "__main__":
    main()
