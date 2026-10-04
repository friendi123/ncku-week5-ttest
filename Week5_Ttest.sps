* Week 5 t-tests in SPSS or PSPP - are these Airbnb differences real or due to chance.
* NCKU | Maxwell K. Hsu.
* Data: Inside Airbnb (insideairbnb.com), NYC snapshot 2026-06-14, CC BY 4.0.
* Put this file and nyc_airbnb_ttest.sav in the same folder.
* If GET FILE fails, open nyc_airbnb_ttest.sav with File > Open > Data and run from the next command.

* Open the data file (30,259 NYC listings).
GET FILE='nyc_airbnb_ttest.sav'.

* ---------------------------------------------------------------.
* Part 1 research question - do superhosts charge a different nightly price from other hosts.
* Independent-samples t-test. Read the row "Equal variances not assumed" (Welch).
* ---------------------------------------------------------------.

* Make a log price so very high prices do not squash the boxplot.
COMPUTE ln_price = LN(price).

* Look first: boxplots of log price for each host type.
EXAMINE VARIABLES=ln_price BY host_type /PLOT=BOXPLOT /STATISTICS=NONE.

* Run the t-test of price for superhosts (1) versus other hosts (2).
T-TEST GROUPS=host_type(1 2) /VARIABLES=price.

* ---------------------------------------------------------------.
* Part 2 research question - is that difference real, or caused by a few extreme listings.
* The same t-test again, without the listings flagged as price outliers.
* ---------------------------------------------------------------.

* Compare the medians: price for each host type (read the Median rows of the Descriptives table).
EXAMINE VARIABLES=price BY host_type /PLOT=NONE /STATISTICS=DESCRIPTIVES.

* Mark the listings that are not price outliers (1 = keep, 0 = set aside).
COMPUTE keep_typical = (price_outlier = 0).

* Use only the kept listings in the next commands.
FILTER BY keep_typical.

* Run the same t-test of price on the typical listings.
T-TEST GROUPS=host_type(1 2) /VARIABLES=price.

* Switch the filter off so later parts use all listings again.
FILTER OFF.

* ---------------------------------------------------------------.
* Part 3 research question - for the same listing, do guests rate cleanliness differently from location.
* Paired-samples t-test.
* ---------------------------------------------------------------.

* Make one difference per listing: cleanliness score minus location score.
COMPUTE gap = review_scores_cleanliness - review_scores_location.

* Look first: histogram of the differences (0 means the same score).
GRAPH /HISTOGRAM=gap.

* Run the paired t-test of cleanliness versus location.
T-TEST PAIRS=review_scores_cleanliness WITH review_scores_location (PAIRED).

* ---------------------------------------------------------------.
* Part 4 research question - is the average listing rated below the superhost standard of 4.8.
* One-sample t-test against the test value 4.8.
* ---------------------------------------------------------------.

* Look first: histogram of the overall ratings.
GRAPH /HISTOGRAM=review_scores_rating.

* Run the one-sample t-test of the overall rating against 4.8.
T-TEST /TESTVAL=4.8 /VARIABLES=review_scores_rating.

* ---------------------------------------------------------------.
* Part 5 research question (your turn) - which costs more per guest, an entire home or a private room.
* Independent-samples t-test on price per guest, without price outliers.
* ---------------------------------------------------------------.

* Make the nightly price per guest.
COMPUTE price_per_guest = price / accommodates.

* Mark entire homes and private rooms that are not price outliers.
COMPUTE keep_home = (price_outlier = 0 AND room_type <= 2).

* Use only the marked listings in the next command.
FILTER BY keep_home.

* Run the t-test of price per guest for entire homes (1) versus private rooms (2).
T-TEST GROUPS=room_type(1 2) /VARIABLES=price_per_guest.

* Switch the filter off so later parts use all listings again.
FILTER OFF.

* ---------------------------------------------------------------.
* Part 6 (optional): rank-based tests, log price, and the Student t-test.
* The Student t-test is the "Equal variances assumed" row of Part 1.
* ---------------------------------------------------------------.

* Mann-Whitney test of price for superhosts versus other hosts (the Part 1 groups).
NPAR TESTS /M-W=price BY host_type(1 2).

* Wilcoxon signed-rank test of cleanliness versus location (the Part 3 pairs).
NPAR TESTS /WILCOXON=review_scores_cleanliness WITH review_scores_location (PAIRED).

* Welch t-test on log price for superhosts versus other hosts.
T-TEST GROUPS=host_type(1 2) /VARIABLES=ln_price.
