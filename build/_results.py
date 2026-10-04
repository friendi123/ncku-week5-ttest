"""Shared loader for handout.qmd and answer_key.qmd: every number in both documents comes from here.

The only source of numbers is expected_results.json (written and verified by run_and_check.py).
"""
import json
import math
import re
import sys
from functools import cache
from pathlib import Path

# Make the build folder importable no matter where the script is run from
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pspp_parse import num, p_text  # noqa: E402

EXPECTED = Path(__file__).resolve().parent / "expected_results.json"
SPS_PATH = Path(__file__).resolve().parent.parent / "Week5_Ttest.sps"
TEST_VALUE = 4.8
ATTRIBUTION = "Data: Inside Airbnb (insideairbnb.com), NYC snapshot 2026-06-14, CC BY 4.0."


@cache
def load() -> dict:
    """The verified results (expected_results.json) as a dict."""
    return json.loads(EXPECTED.read_text(encoding="utf-8"))


# ---------- number formatting ----------

def p_report(cell: str) -> str:
    """'p = .036' or 'p < .001' from a PSPP Sig. cell such as '.036' or '.000'."""
    return "p " + p_text(cell)


def p_float(p: float) -> str:
    """APA p text from an unrounded p-value (used only for values PSPP does not print)."""
    return "p < .001" if p < 0.001 else "p = " + f"{p:.3f}".lstrip("0")


def lead0(cell: str) -> str:
    """Add the leading zero that SPSS drops: '-.94' -> '-0.94', '.50' -> '0.50'."""
    cell = cell.strip()
    if cell.startswith("-."):
        return "-0" + cell[1:]
    return "0" + cell if cell.startswith(".") else cell


def _fixed(x: float, places: int) -> str:
    s = f"{x:.{places}f}"
    return s[1:] if re.fullmatch(r"-0\.0+", s) else s  # never print "-0.00"


def d2(x: float) -> str:
    """Cohen's d to 2 decimals, e.g. '-0.03'."""
    return _fixed(x, 2)


def d3(x: float) -> str:
    """Cohen's d (or a small difference) to 3 decimals, e.g. '-0.029'."""
    return _fixed(x, 3)


def n_text(cell: str) -> str:
    """'6549' -> '6,549'."""
    return f"{int(num(cell)):,}"


def pspp_version() -> str:
    """'1.4.1' from the PSPP version line."""
    return re.search(r"\d+\.\d+\.\d+", load()["meta"]["pspp_version"]).group()


# ---------- derived values ----------

def size_word(d: float) -> str:
    """The notebook's traffic-light reading of Cohen's d."""
    d = abs(d)
    return "tiny" if d < 0.2 else "small" if d < 0.5 else "medium" if d < 0.8 else "large"


def n_outliers() -> int:
    """Price outliers among Part 1's listings (Part 1 n minus Part 2 n, both groups)."""
    r = load()
    return sum(g["n"] for g in r["part1"]["groups"]) - sum(g["n"] for g in r["part2"]["groups"])


def ci_mean_shown() -> tuple[str, str]:
    """Part 4 CI of the mean to 2 decimals, built from PSPP's shown CI of the difference (4.8 + bound),
    so a PSPP student can reproduce it. Must agree with the unrounded SciPy CI of the mean."""
    r = load()["part4"]
    s = r["shown"]
    low, high = (f"{TEST_VALUE + num(s[k]):.2f}" for k in ("ci_low", "ci_high"))
    if (low, high) != (f"{r['ci_mean_low']:.2f}", f"{r['ci_mean_high']:.2f}"):
        raise ValueError(f"Part 4 CI of the mean from the shown cells ({low}, {high}) disagrees with "
                         f"ci_mean_low/high rounded to 2 decimals ({r['ci_mean_low']:.2f}, {r['ci_mean_high']:.2f})")
    return low, high


def ci_mean_arithmetic() -> str:
    """'4.8 + (-.07) = 4.73, and 4.8 + (-.06) = 4.74' from PSPP's shown cells."""
    s = load()["part4"]["shown"]
    low, high = ci_mean_shown()
    return f"{TEST_VALUE} + ({s['ci_low']}) = {low}, and {TEST_VALUE} + ({s['ci_high']}) = {high}"


def d_size_agreement() -> str:
    """Answer-key sentence: do the three d formulas give the same size word (Parts 1, 2, 5)?"""
    r = load()
    differ = [p for p in ("part1", "part2", "part5")
              if len({size_word(r[p][k]) for k in ("d_pooled", "d_colab", "d_pspp_hand")}) > 1]
    if not differ:
        return "All three give the same size word for Parts 1, 2 and 5 (Parts 3 and 4 use one formula in every tool)."
    names = ", ".join(p.replace("part", "Part ") for p in differ)
    return (f"The size word differs between the formulas for {names}: accept either size word there "
            "if the student names the tool and formula. Parts 3 and 4 use one formula in every tool.")


def pooled_from_shown(part: str) -> tuple[float, float]:
    """(pooled SD, d) computed by hand from the rounded Group Statistics values, as a PSPP user would."""
    s = load()[part]["shown"]
    n1, n2 = num(s["n1"]), num(s["n2"])
    sd1, sd2 = num(s["sd1"]), num(s["sd2"])
    sp = math.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / (n1 + n2 - 2))
    return sp, num(s["mean_diff"]) / sp


def hand_d_from_shown(part: str) -> float:
    """Paired (Part 3) or one-sample (Part 4) d from the rounded table: Mean Difference / SD."""
    s = load()[part]["shown"]
    return num(s["mean_diff"]) / num(s["sd_diff"] if part == "part3" else s["sd"])


def significant(part: str) -> bool:
    """Welch (Parts 1, 2, 5) or the part's own test (Parts 3, 4) at alpha = .05."""
    r = load()[part]
    return (r["welch"]["p"] if "welch" in r else r["p"]) < 0.05


def _effect_clause(part: str, d: float, size: str) -> str:
    """'But the effect was tiny' when significant yet tiny, else 'The effect was ...'."""
    lead = "But the effect was" if significant(part) and size == "tiny" else "The effect was"
    return f"{lead} {size} (Cohen's d = {d2(d)})."


# ---------- report sentences ----------

def _independent_report(part: str, name_a: str, name_b: str, verb: str, unit: str) -> str:
    r = load()[part]
    s = r["shown"]
    diff = num(s["mean_diff"])
    direction = "more" if diff > 0 else "less"
    verdict = "a statistically significant" if significant(part) else "no statistically significant"
    return (
        f"{name_a} (M = {s['mean1']}, SD = {s['sd1']}, n = {n_text(s['n1'])}) {verb} "
        f"USD {abs(diff):.2f} {direction} {unit} than {name_b} "
        f"(M = {s['mean2']}, SD = {s['sd2']}, n = {n_text(s['n2'])}) on average. "
        f"Welch's t-test found {verdict} difference, t({s['df_welch']}) = {lead0(s['t_welch'])}, "
        f"{p_report(s['p_welch'])}, 95% CI [{lead0(s['ci_low'])}, {lead0(s['ci_high'])}]. "
        + _effect_clause(part, r["d_pooled"], r["size_word"])
    )


def _part2_report() -> str:
    r = load()
    s1, s2 = r["part1"]["shown"], r["part2"]["shown"]
    p2 = r["part2"]
    tail = (
        f"Welch's t({s2['df_welch']}) = {lead0(s2['t_welch'])}, {p_report(s2['p_welch'])}, "
        f"95% CI [{lead0(s2['ci_low'])}, {lead0(s2['ci_high'])}]; "
        f"Cohen's d = {d2(p2['d_pooled'])}, {p2['size_word']}"
    )
    if significant("part1") and not significant("part2"):
        return (
            f"With all listings, the difference looked significant ({p_report(s1['p_welch'])}). "
            f"Without the {n_outliers():,} Part 1 listings that are flagged as price outliers, the difference was "
            f"not statistically significant ({tail}). "
            "A few extreme prices created the difference. Typical superhosts and other hosts charge about the same."
        )
    return (
        f"With all listings: {p_report(s1['p_welch'])}. Without the {n_outliers():,} Part 1 listings "
        f"that are flagged as price outliers: "
        f"{tail}. Compare the two results and explain what changed."
    )


def _part3_report() -> str:
    r = load()["part3"]
    s = r["shown"]
    return (
        f"Across {n_text(s['n'])} listings, cleanliness scores were {abs(r['mean_diff']):.3f} points "
        f"{'lower' if r['mean_diff'] < 0 else 'higher'} than location scores on average "
        f"(paired t-test, t({s['df']}) = {lead0(s['t'])}, {p_report(s['p'])}, "
        f"95% CI [{d3(r['ci_low'])}, {d3(r['ci_high'])}]). "
        + _effect_clause("part3", r["d"], r["size_word"])
    )


def _part4_report() -> str:
    r = load()["part4"]
    s = r["shown"]
    side = "below" if r["mean"] < TEST_VALUE else "above"
    ci_low, ci_high = ci_mean_shown()
    return (
        f"The average rating was {s['mean']} (SD = {lead0(s['sd'])}, n = {n_text(s['n'])}; "
        f"95% CI of the mean {ci_low} to {ci_high}), "
        f"{side} the superhost standard of {TEST_VALUE} "
        f"(one-sample t-test, t({s['df']}) = {lead0(s['t'])}, {p_report(s['p'])}; "
        f"Cohen's d = {d2(r['d'])}, {r['size_word']})."
    )


def fmt_report(part: str) -> str:
    """APA-style report sentence for one part ('part1' ... 'part5')."""
    if part == "part1":
        return _independent_report("part1", "Superhosts", "other hosts", "charged", "per night")
    if part == "part2":
        return _part2_report()
    if part == "part3":
        return _part3_report()
    if part == "part4":
        return _part4_report()
    if part == "part5":
        return _independent_report("part5", "Entire homes", "private rooms", "cost", "per guest per night")
    raise ValueError(f"No report sentence for {part!r}")


# ---------- tables (Markdown) ----------

def results_table() -> str:
    """Check-your-results table for Parts 1-4: PSPP's shown strings, one column per part."""
    r = load()
    a, b, c, e = (r[p]["shown"] for p in ("part1", "part2", "part3", "part4"))

    def ind(s, key1, key2):
        return f"{s[key1]} / {s[key2]}"

    rows = [
        ("Test", "Welch independent", "Welch independent, outliers out", "Paired", f"One-sample, test value {TEST_VALUE}"),
        ("Groups or variables", "Superhost / Other host", "Superhost / Other host",
         "Cleanliness / Location", "Overall rating"),
        ("N", ind(a, "n1", "n2"), ind(b, "n1", "n2"), c["n"], e["n"]),
        ("Mean", ind(a, "mean1", "mean2"), ind(b, "mean1", "mean2"), ind(c, "mean_x", "mean_y"), e["mean"]),
        ("Levene's F (Sig.)", f"{a['levene_F']} ({a['levene_p']})", f"{b['levene_F']} ({b['levene_p']})",
         "not used", "not used"),
        ("Mean Difference", a["mean_diff"], b["mean_diff"], c["mean_diff"], e["mean_diff"]),
        ("t", a["t_welch"], b["t_welch"], c["t"], e["t"]),
        ("df", a["df_welch"], b["df_welch"], c["df"], e["df"]),
        ("Sig. (2-tailed), as PSPP prints it", a["p_welch"], b["p_welch"], c["p"], e["p"]),
        ("Report as", p_report(a["p_welch"]), p_report(b["p_welch"]), p_report(c["p"]), p_report(e["p"])),
        ("95% CI of the Difference", f"{a['ci_low']} to {a['ci_high']}", f"{b['ci_low']} to {b['ci_high']}",
         f"{c['ci_low']} to {c['ci_high']}", f"{e['ci_low']} to {e['ci_high']} (from {TEST_VALUE})"),
        ("Cohen's d (size)",
         *(f"{d2(r[p]['d_pooled'])} ({r[p]['size_word']})" for p in ("part1", "part2")),
         *(f"{d2(r[p]['d'])} ({r[p]['size_word']})" for p in ("part3", "part4"))),
    ]
    head = "| | Part 1 | Part 2 | Part 3 | Part 4 |\n|---|---|---|---|---|\n"
    return head + "\n".join("| " + " | ".join(row) + " |" for row in rows)


def results_table_note() -> str:
    """Note under the results table: where d comes from, and the Colab values."""
    r = load()
    return (
        "*Note.* Parts 1 and 2 show the \"Equal variances not assumed\" (Welch) row. "
        "Cohen's d for Parts 1 and 2 is the SPSS-style d (mean difference / pooled SD); PSPP does not print it. "
        f"The Colab notebook prints d = {d3(r['part1']['d_colab'])} for Part 1 and "
        f"{d3(r['part2']['d_colab'])} for Part 2 (SPSS-style, to 3 decimals: "
        f"{d3(r['part1']['d_pooled'])} and {d3(r['part2']['d_pooled'])}); "
        + ("the size word is the same. "
           if all(size_word(r[p]["d_colab"]) == r[p]["size_word"] for p in ("part1", "part2"))
           else "check the size word for each formula. ")
        + "For Parts 3 and 4 all tools use the same formula. "
        "See \"Why your Cohen's d may differ slightly\" in Part 1."
    )


def independent_detail_table(part: str) -> str:
    """Answer-key table for an independent-samples part (only PSPP-verified cells)."""
    r = load()[part]
    s = r["shown"]
    g = r["groups"]
    sp, d_hand = pooled_from_shown(part)
    rows = [
        (f"N ({g[0]['label']} / {g[1]['label']})", f"{s['n1']} / {s['n2']}"),
        ("Mean", f"{s['mean1']} / {s['mean2']}"),
        ("Std. Deviation", f"{s['sd1']} / {s['sd2']}"),
        ("Levene's F, Sig.", f"{s['levene_F']}, {s['levene_p']}"),
        ("Equal variances assumed (Student): t, df, Sig.",
         f"{s['t_student']}, {s['df_student']}, {s['p_student']}"),
        ("Equal variances not assumed (Welch): t, df, Sig.",
         f"{s['t_welch']}, {s['df_welch']}, {s['p_welch']} ({p_report(s['p_welch'])})"),
        ("Mean Difference", s["mean_diff"]),
        ("95% CI of the Difference (Welch row)", f"{s['ci_low']} to {s['ci_high']}"),
        ("Cohen's d, SPSS Effect Sizes (pooled SD)", d3(r["d_pooled"])),
        ("Cohen's d, PSPP by hand from the rounded table", f"{d3(d_hand)} (pooled SD = {sp:.2f})"),
        ("Cohen's d, Colab notebook", d3(r["d_colab"])),
        ("Size word", r["size_word"]),
    ]
    return "| Statistic | Value |\n|---|---|\n" + "\n".join(f"| {a} | {b} |" for a, b in rows)


def d_comparison_table() -> str:
    """Answer-key table: Cohen's d by tool for every part."""
    r = load()
    rows = []
    for part, label in (("part1", "Part 1"), ("part2", "Part 2"), ("part5", "Part 5")):
        _, d_hand = pooled_from_shown(part)
        rows.append((label, d3(r[part]["d_pooled"]), d3(d_hand), d3(r[part]["d_colab"]), r[part]["size_word"]))
    for part, label in (("part3", "Part 3"), ("part4", "Part 4")):
        rows.append((label, d3(r[part]["d"]), d3(hand_d_from_shown(part)), d3(r[part]["d"]), r[part]["size_word"]))
    head = ("| Part | SPSS 27+ (pooled SD) | PSPP by hand (rounded table) | Colab notebook | Size word |\n"
            "|---|---|---|---|---|\n")
    return head + "\n".join("| " + " | ".join(row) + " |" for row in rows)


# ---------- syntax excerpts and worked examples ----------

def sps_snippet(start: str, end: str) -> str:
    """Lines of Week5_Ttest.sps from the first line containing `start` to the next line containing `end`,
    as a fenced code block, so the handout quotes the syntax file exactly."""
    lines = SPS_PATH.read_text(encoding="ascii").splitlines()
    i = next(n for n, ln in enumerate(lines) if start in ln)
    j = next(n for n in range(i, len(lines)) if end in lines[n])
    return "```" + chr(10) + chr(10).join(lines[i:j + 1]) + chr(10) + "```"


def worked_example(part: str = "part1") -> str:
    """Pooled-SD Cohen's d by hand from the rounded Group Statistics values (what a PSPP user sees)."""
    s = load()[part]["shown"]
    n1, n2 = int(num(s["n1"])), int(num(s["n2"]))
    sp, d = pooled_from_shown(part)
    return (
        f"pooled SD = √(({n1 - 1:,} × {s['sd1']}² + {n2 - 1:,} × {s['sd2']}²) / {n1 + n2 - 2:,}) = {sp:.2f}; "
        f"d = {lead0(s['mean_diff'])} / {sp:.2f} = {d3(d)}"
    )
