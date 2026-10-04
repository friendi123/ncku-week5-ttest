"""Check the rendered handout and answer key (.docx) against expected_results.json.

Render first (from WEEK5/build; QUARTO_PYTHON must point to a Python that has PyYAML):
    quarto render handout.qmd --output-dir ..
    quarto render answer_key.qmd --output-dir ..
Then run:  python WEEK5/build/check_docs.py

The answer key exists only in the private repo. When build/answer_key.qmd is absent (public repo),
the key checks are skipped; the handout checks, including the Part 5 no-leak check, always run.
"""
import re
import sys
from pathlib import Path

import docx

BUILD = Path(__file__).resolve().parent
WEEK5 = BUILD.parent
HANDOUT = WEEK5 / "Week5_SPSS_Ttest_Practice.docx"
KEY = WEEK5 / "Week5_Ttest_AnswerKey.docx"
SPS = WEEK5 / "Week5_Ttest.sps"
KEY_QMD = BUILD / "answer_key.qmd"
HAS_KEY = KEY_QMD.exists()
SOURCES = [BUILD / "handout.qmd", BUILD / "_results.py", BUILD / "expected_results.json", SPS] + ([KEY_QMD] if HAS_KEY else [])

# Emoji and pictograph ranges (CJK text is allowed; pictographs are not)
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def docx_text(path: Path) -> str:
    """All paragraph text in document order, including paragraphs inside (nested) tables."""
    body = docx.Document(str(path)).element.body
    out = []
    for p in body.xpath(".//w:p"):
        parts = []
        for el in p.xpath(".//w:t | .//w:br | .//w:tab"):
            tag = el.tag.rsplit("}", 1)[-1]
            parts.append((el.text or "") if tag == "t" else "\n" if tag == "br" else "\t")
        out.append("".join(parts))
    return "\n".join(out)


def flat(text: str) -> str:
    """Collapse whitespace so sentences that wrap across runs still match."""
    return re.sub(r"\s+", " ", text)


def section(text: str, start: str, end: str) -> str:
    """Text between the heading line `start` and the next heading line `end`."""
    lines = text.split("\n")
    i = lines.index(start)
    j = lines.index(end, i + 1)
    return "\n".join(lines[i:j])


def main() -> None:
    # 1. Both documents (handout only, without the key) exist and are newer than every source
    for doc in (HANDOUT, KEY) if HAS_KEY else (HANDOUT,):
        assert doc.exists(), f"Missing rendered document: {doc}"
        for src in SOURCES:
            assert doc.stat().st_mtime >= src.stat().st_mtime, f"{doc.name} is older than {src.name}; re-render"

    sys.path.insert(0, str(BUILD))
    from _results import (ci_mean_arithmetic, ci_mean_shown, d2, d3, d_size_agreement,  # noqa: E402
                          fmt_report, load, n_outliers, p_report)

    r = load()
    handout_text = docx_text(HANDOUT)
    h = flat(handout_text)
    docs = [(h, "handout")]
    if HAS_KEY:
        key_text = docx_text(KEY)
        k = flat(key_text)
        docs.append((k, "key"))

    # 2. Structure of the handout
    for heading in ["Stats in 5 minutes", "Choosing a test", "Reading SPSS output",
                    "Part 1", "Part 2", "Part 3", "Part 4", "Part 5", "Part 6", "Check your results",
                    "Try it with AI", "Which tool should I use?", "Open the data"]:
        assert heading in handout_text, f"Handout heading missing: {heading}"
    assert "Why your Cohen's d may differ slightly" in handout_text
    assert "Tests of Normality" in handout_text, "PSPP note about the empty Tests of Normality table missing"

    # Every command of the syntax file is quoted exactly in the handout
    for line in SPS.read_text(encoding="ascii").splitlines():
        if line.strip() and not line.startswith("*"):
            assert line in handout_text, f"Syntax line not quoted exactly in the handout: {line}"

    # 3. p-value wording, author line, attribution, no emojis, no placeholders
    for text, name in docs:
        assert "p < .001" in text, f"p < .001 wording missing in {name}"
        assert "p = .000" not in text and "p = 0" not in text, f"Bad p wording in {name}"
        assert "NCKU | Maxwell K. Hsu" in text, f"Author line missing in {name}"
        assert "Data: Inside Airbnb (insideairbnb.com), NYC snapshot 2026-06-14, CC BY 4.0." in text, name
        assert not EMOJI_RE.search(text), f"Emoji in {name}: {EMOJI_RE.search(text).group()!r}"
        assert not re.search(r"TODO|TBD|\{\{|\?\?|\{python\}", text), f"Placeholder left in {name}"
    assert "p 值" in handout_text, "Traditional Chinese key term for p-value missing"

    # 4. Check-your-results table (Parts 1-4) holds the PSPP shown strings and d to 2 decimals
    table = section(handout_text, "Check your results", "Try it with AI")
    for part in ("part1", "part2"):
        s = r[part]["shown"]
        for key in ("n1", "n2", "mean1", "mean2", "mean_diff", "t_welch", "df_welch", "p_welch",
                    "ci_low", "ci_high", "levene_F", "levene_p"):
            assert s[key] in table, f"{part} {key} = {s[key]} missing from results table"
        assert d2(r[part]["d_pooled"]) in table and r[part]["size_word"] in table
        assert d3(r[part]["d_colab"]) in table, f"{part} Colab d footnote missing"
    for part in ("part3", "part4"):
        s = r[part]["shown"]
        for key in ("n", "mean_diff", "t", "df", "p", "ci_low", "ci_high"):
            assert s[key] in table, f"{part} {key} = {s[key]} missing from results table"
        assert d2(r[part]["d"]) in table and r[part]["size_word"] in table
    assert "Part 5" not in table and "Part 6" not in table, "Results table must cover Parts 1-4 only"

    # 5. Part 5 numbers appear in the key and never in the handout
    # (the public repo's trimmed expected_results.json has no Part 5 or Part 6 at all)
    has_part5 = "part5" in r
    assert has_part5 or not HAS_KEY, "The answer key needs the full expected_results.json"
    s5 = r["part5"]["shown"] if has_part5 else {}
    for key in ("t_welch", "df_welch", "p_welch", "mean1", "mean2", "ci_high") if has_part5 else ():
        assert s5[key] not in handout_text, f"Part 5 {key} = {s5[key]} leaked into the handout"
        if HAS_KEY:
            assert s5[key] in key_text, f"Part 5 {key} missing from key"
    if HAS_KEY:
        assert p_report(s5["p_welch"]) in k

    # 6. Report sentences: Parts 1-4 in both documents, Part 5 in the key only
    for part in ("part1", "part2", "part3", "part4"):
        sentence = flat(fmt_report(part))
        for text, name in docs:
            assert sentence in text, f"{part} report sentence missing from {name}"
    if has_part5:
        assert flat(fmt_report("part5")) not in h, "Part 5 report sentence leaked into the handout"
    if HAS_KEY:
        assert flat(fmt_report("part5")) in k

    # 7. Lessons follow the numbers
    assert r["part1"]["welch"]["p"] < 0.05 and r["part2"]["welch"]["p"] >= 0.05
    assert "not statistically significant" in section(handout_text, next(
        ln for ln in handout_text.split("\n") if ln.startswith("Part 2:")), next(
        ln for ln in handout_text.split("\n") if ln.startswith("Part 3:"))), "Part 2 lesson must say not significant"
    assert f"Cohen's d = {d2(r['part3']['d'])}" in h and r["part3"]["size_word"] in h

    # 8. Effect-size alert: worked example from Part 1 shown values, Hedges' g, formula
    assert d3(r["part1"]["d_pspp_hand"]) in h, "Worked pooled-SD example result missing"
    assert "Hedges' g" in h and "pooled SD" in h

    # 9. Part 4: CI of the difference vs CI of the mean is explained
    assert "add 4.8" in h

    # 10. Answer key extras
    if HAS_KEY:
        for needle in ("Not machine-verified", "Effect Sizes", "Colab", "Mann-Whitney", "Wilcoxon"):
            assert needle in k, f"Key missing: {needle}"
        for part in ("part1", "part2", "part5"):
            assert d3(r[part]["d_colab"]) in k and d3(r[part]["d_pooled"]) in k
        p6 = r["part6"]
        assert p_report(p6["shown"]["mw_p"]) in k and p_report(p6["shown"]["ln_welch_p"]) in k

    # 11. Final-review fixes
    # Cohen's d scale includes "small", matching size_word()
    assert "under 0.2 tiny, 0.2 to 0.5 small, 0.5 to 0.8 medium, 0.8 or more large" in h, "d scale wording"
    # Rank tests described correctly (old sentence gone)
    assert "Mann-Whitney and Wilcoxon tests compare which group" not in h, "Old Wilcoxon wording still present"
    assert "tend to be above or below zero" in h and "tends to have higher values" in h
    # SPSS users note: more decimals, Two-Sided p
    assert "SPSS users" in handout_text and "Two-Sided p" in h and "One-Sided p" in h, "SPSS users note missing"
    assert "as PSPP prints it" in table and "as printed" not in table.replace("as PSPP prints it", "")
    if HAS_KEY:
        assert "Two-Sided p" in k and "more decimals" in k, "Key's Not machine-verified list lacks SPSS output notes"
    # Part 4: CI of the mean to 2 decimals from PSPP's shown cells, agreeing with SciPy
    p4 = r["part4"]
    assert ci_mean_shown() == (f"{p4['ci_mean_low']:.2f}", f"{p4['ci_mean_high']:.2f}")
    assert ci_mean_arithmetic() in h, "Part 4 CI-of-the-mean arithmetic missing"
    assert not re.search(r"4\.8 \+ \(-?0?\.\d{3}", h), "3-decimal Part 4 arithmetic still present"
    assert f"95% CI of the mean {ci_mean_shown()[0]} to {ci_mean_shown()[1]}" in h
    assert "PSPP's table rounds to two decimals" in h
    # Part 2 medians: Explore with Statistics on price; no median numbers quoted (not SciPy-verified)
    assert "Display: Statistics" in h and "Dependent List: price" in h
    # pspp_output.csv is written by run_and_check.py, which the public repo does not have
    pspp_out = BUILD / "pspp_output.csv"
    assert pspp_out.exists() or not (BUILD / "run_and_check.py").exists(), "Run run_and_check.py first"
    if pspp_out.exists():
        pspp_csv = pspp_out.read_text(encoding="utf-8")
        medians = re.findall(r"^,+Median,,([\d.]+),", pspp_csv, flags=re.M)
        assert len(medians) == 3, f"Expected 3 PSPP Median cells, found {medians}"
        for m in medians:
            assert m not in h, f"Median {m} quoted in the handout"
    # Outlier count wording (computed, not typed)
    for text, name in docs:
        assert f"{n_outliers():,} Part 1 listings that are flagged as price outliers" in text, name
    # Key: size-word agreement sentence follows the numbers
    if HAS_KEY:
        assert d_size_agreement() in k
        print(f"Handout: {len(handout_text):,} characters; key: {len(key_text):,} characters")
    else:
        print(f"Handout: {len(handout_text):,} characters; answer key not present, key checks skipped")
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
