"""Tests for pspp_parse: table reader, number helpers and the PSPP runner."""
import sys
import tempfile
from pathlib import Path

# Make the build folder importable no matter where the script is run from
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pspp_parse  # noqa: E402
from pspp_parse import decimals, matches, num, p_text, read_tables, run_pspp  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_read_tables() -> None:
    tables = read_tables(FIXTURES / "probe.csv")
    titles = [t.title for t in tables]
    assert titles.count("Independent Samples Test") == 1 and titles.count("Test Statistics") == 2
    ind = next(t for t in tables if t.title == "Independent Samples Test")
    welch = next(r for r in ind.rows if r[1] == "Equal variances not assumed")
    assert welch[4:7] == ["-2.93", "1.48", ".139"]


def test_helpers() -> None:
    assert num(".026") == 0.026 and num("7,096") == 7096 and num("-3.44") == -3.44
    assert num("7096") == 7096 and decimals(".000") == 3 and decimals("7096") == 0
    assert p_text(".000") == "< .001" and p_text(".036") == "= .036"
    assert matches(".139", 0.13949) and not matches(".139", 0.1396)


def test_run_pspp() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        out = tmp / "probe.csv"
        version = run_pspp(FIXTURES / "probe.sps", out, tmp)
        assert version.startswith("pspp (GNU PSPP) 1.4.1"), version
        # Compare ignoring blank lines
        def lines(p: Path) -> list[str]:
            return [x for x in p.read_text().splitlines() if x.strip()]
        assert lines(out) == lines(FIXTURES / "probe.csv")
        bad = tmp / "bad.sps"
        bad.write_text("FREQUENCIES nosuchvar.\n")
        try:
            run_pspp(bad, tmp / "bad.csv", tmp)
        except RuntimeError as e:
            assert "error" in str(e).lower()
        else:
            raise AssertionError("run_pspp did not raise on a bad syntax file")


def test_run_pspp_ignores_stale_output() -> None:
    """A crash before writing must not let run_pspp scan an old output file."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        out = tmp / "stale.csv"
        out.write_text("warning: stale line from an earlier run\n")
        # Stand-in for PSPP: Python runs the "syntax file", which exits 1 without writing output
        crash = tmp / "crash.sps"
        crash.write_text("import sys\nsys.exit(1)\n")
        saved = pspp_parse.PSPP_EXE
        pspp_parse.PSPP_EXE = Path(sys.executable)
        try:
            run_pspp(crash, out, tmp)
        except RuntimeError as e:
            assert "stale" not in str(e), str(e)
        else:
            raise AssertionError("run_pspp did not raise on a crash")
        finally:
            pspp_parse.PSPP_EXE = saved  # restore the real path even if an assertion fails
        assert not out.exists(), "run_pspp left the stale output file in place"


if __name__ == "__main__":
    test_read_tables()
    test_helpers()
    test_run_pspp()
    test_run_pspp_ignores_stale_output()
    print("ALL TESTS PASSED")
