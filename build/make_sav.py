"""Build nyc_airbnb_ttest.sav (9 coded variables) from the Week 3 cleaned NYC Airbnb CSV."""
import platform
import subprocess
from pathlib import Path

import pandas as pd
import pyreadstat
import scipy

# Folder that holds the deliverables (this script lives in WEEK5/build)
WEEK5 = Path(__file__).resolve().parent.parent
CSV_PATH = Path(
    "C:/Users/xiada/Downloads/Wave_NCKU_DigitalMar_AI-Excel_Tableau/"
    "ncku-dataviz-colab/data/nyc_listings_clean_2026-06-14.csv"
)
SAV_PATH = WEEK5 / "nyc_airbnb_ttest.sav"
from pspp_parse import PSPP_EXE  # noqa: E402  single home of the PSPP path

# Numeric codes for the string variables
ROOM_CODES = {"Entire home/apt": 1, "Private room": 2, "Hotel room": 3, "Shared room": 4}
HOST_CODES = {"t": 1, "f": 2}

COLUMN_LABELS = {
    "id": "Listing ID",
    "host_type": "Host type",
    "room_type": "Room type",
    "accommodates": "Number of guests",
    "price": "Nightly price (USD)",
    "price_outlier": "Extreme price (flagged in Week 3 cleaning)",
    "review_scores_rating": "Overall rating (0-5)",
    "review_scores_cleanliness": "Cleanliness rating (0-5)",
    "review_scores_location": "Location rating (0-5)",
}
VALUE_LABELS = {
    "host_type": {1: "Superhost", 2: "Other host"},
    "room_type": {1: "Entire home/apt", 2: "Private room", 3: "Hotel room", 4: "Shared room"},
    "price_outlier": {0: "No", 1: "Yes"},
}
FORMATS = {
    "id": "F12.0",
    "host_type": "F1.0",
    "room_type": "F1.0",
    "accommodates": "F3.0",
    "price": "F8.2",
    "price_outlier": "F1.0",
    "review_scores_rating": "F5.3",
    "review_scores_cleanliness": "F5.3",
    "review_scores_location": "F5.3",
}
MEASURES = {
    "id": "nominal",
    "host_type": "nominal",
    "room_type": "nominal",
    "accommodates": "scale",
    "price": "scale",
    "price_outlier": "nominal",
    "review_scores_rating": "scale",
    "review_scores_cleanliness": "scale",
    "review_scores_location": "scale",
}


def build_frame(csv_path: Path) -> pd.DataFrame:
    """Read the CSV and return the 9 coded variables; no rows are dropped."""
    raw = pd.read_csv(csv_path)
    out = pd.DataFrame()
    out["id"] = raw["id"].astype("float64")
    # Unknown host type (NaN) stays system-missing because map() returns NaN
    out["host_type"] = raw["host_is_superhost"].map(HOST_CODES).astype("float64")
    # Any non-missing host value other than "t"/"f" would silently become missing, so fail loudly
    bad_host = raw["host_is_superhost"].notna() & out["host_type"].isna()
    if bad_host.any():
        raise ValueError(f"unmapped host_is_superhost values: {raw.loc[bad_host, 'host_is_superhost'].unique()}")
    out["room_type"] = raw["room_type"].map(ROOM_CODES).astype("float64")
    out["accommodates"] = raw["accommodates"].astype("float64")
    out["price"] = raw["price"].astype("float64")
    # Boolean flag to 0/1 (works for True/False or "True"/"False" strings)
    out["price_outlier"] = raw["price_outlier"].astype(str).str.lower().map({"true": 1.0, "false": 0.0})
    for col in ["review_scores_rating", "review_scores_cleanliness", "review_scores_location"]:
        out[col] = raw[col].astype("float64")
    # Fail loudly if any mapping produced unexpected missing values
    if out["room_type"].isna().any():
        raise ValueError("unmapped room_type")
    if out["price_outlier"].isna().any():
        raise ValueError("unmapped price_outlier")
    return out[list(COLUMN_LABELS)]


def write_sav(df: pd.DataFrame, out_path: Path) -> None:
    """Write the frame to .sav with labels, print formats and measurement levels."""
    pyreadstat.write_sav(
        df,
        str(out_path),
        column_labels=[COLUMN_LABELS[c] for c in df.columns],
        variable_value_labels=VALUE_LABELS,
        variable_format=FORMATS,
        variable_measure=MEASURES,
    )


def main() -> None:
    """Build the file, compare row counts before and after, and print versions."""
    df = build_frame(CSV_PATH)
    n_csv = len(pd.read_csv(CSV_PATH, usecols=["id"]))
    write_sav(df, SAV_PATH)
    back, _ = pyreadstat.read_sav(str(SAV_PATH))
    print(f"Rows in CSV: {n_csv}; rows in .sav: {len(back)}")
    if n_csv != len(back):
        raise SystemExit("Row count changed between CSV and .sav")
    res = subprocess.run([str(PSPP_EXE), "--version"], capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit("pspp --version failed")
    pspp = res.stdout.splitlines()[0]
    print(f"Python {platform.python_version()}, pandas {pd.__version__}, SciPy {scipy.__version__}, "
          f"pyreadstat {pyreadstat.__version__}, {pspp}")


if __name__ == "__main__":
    main()
