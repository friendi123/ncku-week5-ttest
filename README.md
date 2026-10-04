# Week 5: Are These Airbnb Differences Real?

A practice exercise on **t-tests (t 檢定)** with real New York City Airbnb data. You can use **IBM SPSS**, the free **GNU PSPP**, or **Google Colab**.

## Start here

**1. Download the files.** Click the green **Code** button near the top of this page, choose **Download ZIP**, and unzip (extract) the folder on your computer. Do not work inside the ZIP file.

You need these three files:

| File | What it is |
|---|---|
| [`Week5_SPSS_Ttest_Practice.pdf`](Week5_SPSS_Ttest_Practice.pdf) | **The handout. Read this first.** It walks you through every step. |
| [`nyc_airbnb_ttest.sav`](nyc_airbnb_ttest.sav) | The data: 30,259 NYC Airbnb listings, ready for SPSS and PSPP. |
| [`Week5_Ttest.sps`](Week5_Ttest.sps) | The syntax file: the SPSS/PSPP commands for every part. |

You can also download one file at a time: click the file name, then click the download button (Download raw file) at the top right.

**2. Pick one tool.** All three give the same answers.

| Tool | Cost | What to open |
|---|---|---|
| IBM SPSS (version 27 or later) | University licence | `nyc_airbnb_ttest.sav` and `Week5_Ttest.sps` |
| GNU PSPP | Free: [gnu.org/software/pspp](https://www.gnu.org/software/pspp/) | The same two files |
| Google Colab | Free (Google account) | [Open the t-test notebook in Colab](https://colab.research.google.com/github/friendi123/ncku-dataviz-colab/blob/main/notebooks/03_ttest_airbnb.ipynb). It loads the data by itself, so you do not need the `.sav` file. |

**3. Put the `.sav` and `.sps` files in the same folder** (they already are, if you unzipped the ZIP file).

**4. Work through the handout in order.**

- Parts 1-5 are the core track. Everyone does them.
- Part 6 is optional and not graded.
- Run the parts **in order**: Part 6 uses a variable that Part 1 creates.
- Stuck? Read the **Stuck?** tip at the end of each part.

**5. Check your work.** The **Check your results** table at the end of the handout lists the numbers you should get for Parts 1-4.

**Part 5 is your turn.** No answers are given for Part 5. Write your own research question, hypotheses, and report sentence, then hand in your work the way your instructor tells you.

## Common problems

| Problem | What to do |
|---|---|
| `GET FILE` fails in SPSS | SPSS looks in its own working folder. Open the data with File > Open > Data, then run the syntax from the next command. |
| My SPSS numbers have more decimals than the handout | The handout shows what PSPP prints. Round your numbers to the decimals in the handout before you compare. |
| SPSS 27+ shows two p-value columns | Read **Two-Sided p** (never One-Sided p). It is the same as "Sig. (2-tailed)". |
| PSPP shows an empty "Tests of Normality" table | Ignore it; the boxplot is what you need. |
| My Cohen's d is slightly different | Tools use different formulas. See "Why your Cohen's d may differ slightly" in Part 1 of the handout. |
| Sig. shows ".000" | That means **p < .001**. Never write p = .000. |

## You can ignore the `build` folder

The `build` folder holds the code that produces the handout and checks every number in it. It is for the instructor. You do not need it for the exercise.

## Data

Data: Inside Airbnb (insideairbnb.com), NYC snapshot 2026-06-14, CC BY 4.0. The data were cleaned in Week 3; listings with extreme prices are flagged in the `price_outlier` variable. The handout's numbers were checked with GNU PSPP 1.4.1.
