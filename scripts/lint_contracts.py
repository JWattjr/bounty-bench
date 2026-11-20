"""Run the pinned GenVM linter on every deployable contract source."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = [ROOT / "contracts" / name for name in ("bounty_board.py", "patch_judge.py", "issue_scout.py")]


def main():
    failed = False
    for source in CONTRACTS:
        result = subprocess.run(
            [sys.executable, "-m", "genvm_linter.cli", "check", str(source), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(source.name, "could not parse linter output")
            print(result.stdout[-1500:])
            print(result.stderr[-1500:])
            failed = True
            continue
        ok = result.returncode == 0 and report.get("ok") is True
        print(source.name, "PASS" if ok else "FAIL")
        if not ok:
            print(json.dumps(report.get("lint", {}), indent=2))
            failed = True
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
