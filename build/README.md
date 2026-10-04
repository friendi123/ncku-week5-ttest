# Build files (for the instructor)

**Students: you do not need anything in this folder.** Go back to the [main page](../README.md) and start with the handout, `Week5_SPSS_Ttest_Practice.pdf`.

This folder holds the code that builds the handout and checks its numbers:

| File | What it does |
|---|---|
| `make_sav.py` | Builds `nyc_airbnb_ttest.sav` from the cleaned Inside Airbnb CSV (the CSV is not included). |
| `pspp_parse.py` | Reads PSPP output tables. |
| `expected_results.json` | The verified numbers the handout prints (Parts 1-4). |
| `_results.py` | Formats those numbers for the handout. |
| `handout.qmd` | The handout source (Quarto). |
| `check_docs.py` | Checks the rendered handout against `expected_results.json` and the syntax file. |
| `build.ps1` | Runs the whole build on Windows (needs Python, PSPP, Quarto, and Microsoft Word). |
| `test_*.py`, `fixtures/` | Tests. |
