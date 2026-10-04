"""Run PSPP and read its CSV output tables (used to compare PSPP with SciPy)."""
import csv
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Single home of the PSPP executable path
PSPP_EXE = Path("C:/Program Files/PSPP/bin/pspp.exe")

# PSPP reports problems as "file:line: error: ..." or "...: warning: ..."
_PROBLEM = re.compile(r"(error|warning):", re.IGNORECASE)


@dataclass
class Table:
    """One output table: its title and its CSV rows (header rows included)."""
    title: str
    rows: list[list[str]]


def run_pspp(sps_path: Path, out_csv: Path, cwd: Path) -> str:
    """Run a syntax file; raise on non-zero exit or any error/warning line; return version line."""
    version = subprocess.run(
        [str(PSPP_EXE), "--version"], capture_output=True, text=True, check=True
    ).stdout.splitlines()[0]
    # Remove any earlier output so a crash before writing cannot leave a stale file to scan
    out_csv.unlink(missing_ok=True)
    res = subprocess.run(
        [str(PSPP_EXE), str(sps_path), "-o", str(out_csv)],
        capture_output=True, text=True, cwd=str(cwd),
    )
    # PSPP may print messages to stdout, stderr, or the output file
    text = res.stdout + "\n" + res.stderr
    if out_csv.exists():
        text += "\n" + out_csv.read_text(encoding="utf-8", errors="replace")
    problems = [ln for ln in text.splitlines() if _PROBLEM.search(ln)]
    if res.returncode != 0 or problems:
        raise RuntimeError(
            f"PSPP failed (exit {res.returncode}) on {sps_path}:\n" + "\n".join(problems)
        )
    return version


def read_tables(csv_path: Path) -> list[Table]:
    """Split a PSPP CSV file into tables; each block starts at a 'Table: <title>' line."""
    tables: list[Table] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if row and row[0].startswith("Table: "):
                tables.append(Table(row[0][len("Table: "):], []))
            elif tables and any(c.strip() for c in row):
                tables[-1].rows.append(row)  # blank separator rows are skipped
    return tables


def num(cell: str) -> float:
    """Parse a PSPP number such as '.026', '-3.44' or '7,096'."""
    return float(cell.replace(",", "").strip())


def decimals(cell: str) -> int:
    """Count digits after the decimal point ('.000' -> 3)."""
    cell = cell.strip()
    return len(cell.split(".")[1]) if "." in cell else 0


def p_text(cell: str) -> str:
    """APA-style p text; '.000' means below .0005 so report '< .001'."""
    return "< .001" if num(cell) == 0 else "= " + cell.strip()


def matches(shown: str, value: float) -> bool:
    """True if the displayed (rounded) number agrees with value to its last shown digit."""
    return abs(num(shown) - value) <= 0.5 * 10 ** -decimals(shown) + 1e-12
