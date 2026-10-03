# Model and evaluation protocol

Every game has a declared orientation A/B. The seed feature is
`(seed_B - seed_A) / 15`. Logistic regression has no intercept, ensuring that
swapping opponents negates the feature vector and complements the probability.
Equal seeds receive 50% under seed-only models. Tournament wins and scores are
labels or display data; they are never inputs to a game prediction.

The seed-curve challenger adds `log(seed_B / seed_A) / log(16)`.
The form challenger adds `(Elo_A - Elo_B) / 400`, win-rate difference, and
mean-margin difference divided by 20. These are fixed domain scales; none is
fitted using a future test year. The ridge penalty is 1.0 on the summed negative
log likelihood. Newton iteration stops at a small step or 80 iterations.
Hyperparameters were fixed for this first version; no holdout search is performed.

Within-season Elo starts every team at 1500. K=20; a nonneutral home team gets
60 rating points for its expected-score calculation. Ratings update after each
completed, non-tied game in timestamp/ID order. No postseason or March results
are used in the form feature snapshot: the cutoff is March 1, 00:00 UTC each
season. At least ten completed games are required per team. The schedules may
include opponents outside Division I; their ratings also start at 1500. This is
a simple schedule rating, not an adjusted-efficiency or official ranking model.

Seeds come from tournament selection. Form comes from the earlier March 1
horizon. Neither model predicts qualification or seed assignment. Historical
64-team fields exclude preliminary-round losers; this conditions bracket
experiments on participants known after preliminary games. Later-round game
evaluations condition on actual matchup identities, whereas bracket advancement
odds integrate the possible matchups.

Seed models warm up on 1985–1994 and score annually from 1995. Form models fit
only when at least 100 earlier paired labels have available features. For a year
Y, coefficients use seasons `< Y`. A temperature in [0.75,1.5] is fitted to raw
out-of-fold predictions from years `< Y`; at least 189 earlier predictions are
required, otherwise temperature is 1. All fit/calibration boundaries are stored
in `artifacts/historical_models.json` and `artifacts/predictions.json`.

2021–2026 is a chronological **rolling** holdout. The annual refit can consume
earlier test-season results for a later test season. It never consumes the
current tournament. It was inspected during implementation, and therefore is
not an untouched research lockbox or a prospective track record. No challenger
is promoted from this holdout: the seed baseline remains primary.

Brier and natural-log loss are computed on one row per played game. Accuracy
uses half credit for a probability tie. Reliability curves mirror opponent
orientation so their bins describe probabilities across the full [0,1] range.
Mirroring does not double the effective sample; holdout n remains 377. ECE is
the weighted absolute reliability gap in ten equal-width bins, sensitive to bin
choice and sample size. The coin baseline's zero ECE is a consequence of its
symmetric 50% predictions; it has no discrimination.

Paired Brier uncertainty resamples whole holdout tournaments 5,000 times with a
fixed random seed. All compared rows share game IDs. Only six test tournaments
exist, so the reported intervals are unstable and do not establish future skill.
The final corrected form model is slightly worse than the seed baseline. Two
ambiguous source-name labels were corrected before the final evaluation:
Lafayette→Louisiana in 2023 and SanDiego→UC San Diego in 2025.

The prospective 2027 artifacts refit on all 2,582 labels through 2026, and
calibrate on available earlier rolling predictions. Form coefficients are
trained on 1,259 modern game labels; 2027 form features do not exist yet. The
UI uses the seed model for imported 2027 fields. Opening-game opponents sharing
a seed receive 50% under that model. Opening games have not been evaluated in
the historical corpus, so these probabilities are an extrapolation of the
declared symmetric model rather than a measured Opening Round record.

Exact bracket probabilities use dynamic programming over the declared tree:
each winner distribution is the sum over opposing child distributions of
`P(reach A) * P(reach B) * P(A beats B)`. Fixed pairwise probabilities imply
conditional independence. A seeded PRNG also draws one complete valid bracket.
No fitted-parameter uncertainty, roster shocks or cross-game latent-strength
correlations are included. Probabilities can therefore be more certain than a
full uncertainty model would be.
