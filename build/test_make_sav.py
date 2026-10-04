"""Test that nyc_airbnb_ttest.sav has the agreed counts, labels, formats and measures."""
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pyreadstat

# Make the build folder importable no matter where the script is run from
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_sav import (  # noqa: E402
    COLUMN_LABELS, CSV_PATH, FORMATS, PSPP_EXE, SAV_PATH, VALUE_LABELS,
)

# Expected measurement levels from the brief
NOMINAL = {"id", "host_type", "room_type", "price_outlier"}


def test_contents() -> None:
    """Check literal counts from the brief."""
    df, meta = pyreadstat.read_sav(str(SAV_PATH))
    assert len(df) == 30259
    assert df["host_type"].isna().sum() == 349
    assert (df["host_type"] == 1).sum() == 7096 and (df["host_type"] == 2).sum() == 22814
    assert df["room_type"].value_counts().to_dict() == {1: 16808, 2: 12713, 3: 520, 4: 218}
    assert df["price"].isna().sum() == 8744
    assert (df["price_outlier"] == 1).sum() == 747
    assert df["review_scores_rating"].notna().sum() == 21700
    assert df["review_scores_location"].notna().sum() == 21691
    assert meta.variable_value_labels["host_type"] == {1.0: "Superhost", 2.0: "Other host"}
    assert meta.original_variable_types["price"] == "F8.2"


def test_against_csv() -> None:
    """Check the .sav read back matches counts computed independently from the CSV."""
    raw = pd.read_csv(CSV_PATH)
    df, _ = pyreadstat.read_sav(str(SAV_PATH))
    assert len(df) == len(raw)
    host = raw["host_is_superhost"]
    assert (df["host_type"] == 1).sum() == (host == "t").sum()
    assert (df["host_type"] == 2).sum() == (host == "f").sum()
    assert df["host_type"].isna().sum() == host.isna().sum()
    assert df["room_type"].value_counts().sort_index().tolist() == [
        (raw["room_type"] == r).sum()
        for r in ["Entire home/apt", "Private room", "Hotel room", "Shared room"]
    ]
    outlier = raw["price_outlier"].astype(str).str.lower()
    assert (df["price_outlier"] == 1).sum() == (outlier == "true").sum()
    assert (df["price_outlier"] == 0).sum() == (outlier == "false").sum()
    for col in ["price", "review_scores_rating", "review_scores_cleanliness", "review_scores_location"]:
        assert df[col].isna().sum() == raw[col].isna().sum(), col


def test_metadata() -> None:
    """Check variable labels, value labels, formats and measurement levels."""
    _, meta = pyreadstat.read_sav(str(SAV_PATH))
    assert meta.column_names == list(COLUMN_LABELS)
    assert dict(zip(meta.column_names, meta.column_labels)) == COLUMN_LABELS
    for var, labels in VALUE_LABELS.items():
        assert meta.variable_value_labels[var] == {float(k): v for k, v in labels.items()}, var
    assert {k: v for k, v in meta.original_variable_types.items()} == FORMATS
    for var, measure in meta.variable_measure.items():
        assert measure == ("nominal" if var in NOMINAL else "scale"), var
    assert len(meta.variable_measure) == 9


def test_pspp_reads() -> None:
    """Check PSPP opens the file and shows N, a variable label (wrapped in narrow table cells, so a short one is used), value label, format and measure."""
    with tempfile.TemporaryDirectory() as tmp:
        sps = Path(tmp) / "check.sps"
        # Forward slashes keep the path valid inside PSPP syntax
        sps.write_text(
            f"GET FILE='{SAV_PATH.as_posix()}'.\nDISPLAY DICTIONARY.\nDESCRIPTIVES VARIABLES=id.\n",
            encoding="ascii",
        )
        res = subprocess.run([str(PSPP_EXE), str(sps)], capture_output=True, text=True, cwd=tmp)
    assert res.returncode == 0, res.stderr
    for text in ["host_type", "30259", "Listing ID", "F8.2", "Superhost", "Nominal"]:
        assert text in res.stdout, f"{text!r} not in PSPP output:\n{res.stdout}"


if __name__ == "__main__":
    test_contents()
    test_against_csv()
    test_metadata()
    test_pspp_reads()
    print("ALL TESTS PASSED")
