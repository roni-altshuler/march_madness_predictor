# Integer pick track record

`/api/track-record` and the identical exported `data/track_record.json` derive the
primary seed baseline's record from existing saved files. They do not train or
regenerate models, probabilities, fixtures, results or forecasts.

The default fixed 2021–2026 held-out period comes from `artifacts/evaluation.json`.
Join `artifacts/predictions.json` seed records to `data/derived/archive.json` by
game ID. Require a played outcome, known UTC event time no later than the bundled
snapshot date, matching result/round/season, and training/calibration metadata
consistent with the strictly earlier snapshot in `artifacts/historical_models.json`.
Exclude duplicate event rows rather than choosing a favorable prediction. The
report includes exclusion counts and source-file SHA-256 hashes.

Pick the higher saved probability; exact p=0.5 selects bracket-order side A, the
existing bracket rule. A correct pick earns integer 1; an incorrect pick earns 0.
The bundled record is **269 / 377 = 71.4%**, excluding the 2021 Oregon–VCU
no-contest. This is not accuracy for a coherently filled bracket: later-round
records use the actual matchups. First Four games and preliminary losers are not
covered. Legacy `metrics()` half-credit tie accuracy remains separately labelled;
never multiply that percentage by n to reconstruct integer wins.

Calendar points close observed UTC ISO weeks, including partial weeks, with no
invented zero-game weeks. Cumulative totals pool integer counts, never average
weekly percentages. Recent form is fixed at the last **20 eligible settled games**,
reset each tournament, with actual smaller denominators at startup. UTC event
time then game ID resolves equal-time ordering deterministically. Week/year
rollover does not itself reset the window. Every point exposes its weekly,
cumulative and recent numerator/denominator and recent start/end dates. Straight
line segments connect observations without smoothing or forced improvement.

Historical snapshots were produced retrospectively and the holdout was inspected
during implementation. They are neither prospective forecasts nor an unseen
lockbox. No genuine timestamped pre-event published ledger is bundled, so the
prospective view is **Not yet scored**, not 0%. The scoring function's optional
prospective input requires an explicit saved seed-model pick and known issued and
published times, with issue <= publication < event, plus a settled eligible result.
Unknown, late, duplicate, unsettled and future events do not become scored picks.
No dated public release history is available; no version markers are invented.
The unannounced 2027 field receives no invented predictions or results.

The bracket-first home adds a compact labelled record link. `#record` provides
the full date timeline, native keyboard/touch point controls, an exact-count table,
all eligible pick/result rows, and source audit. API and static builds share the
same Python report. No accuracy guarantee or AI success claim is implied.

The tournament-season selector scopes the headline, every pick/result row and
calendar counts together. A season's cumulative line starts from its own first
eligible game; it does not inherit earlier tournaments' numerators. The full
holdout still reconciles to 269 / 377. For example, 2021 is 43 / 62 after its one
no-contest is excluded, and 2026 is 46 / 63. These remain retrospective results.

Outcome picks appear beside actual winners in responsive rows before the optional
calendar disclosure. Both outcomes fit on narrow screens without horizontal
scrolling. The saved pick's probability and publication/training audit remain
available. Exact-score forecasts are not produced; no score-error metric is
invented. Game-result accuracy is separate from filled-bracket advancement,
which has no archived pre-event pick ledger and remains unrecorded.

Coverage counts unique archived games: no-contests, known settled played results,
and unavailable/unsettled results. Known results without an eligible saved pick
are shown separately and never counted as incorrect. Source rejection diagnostics
still count rejected input rows, so duplicates can produce multiple rejected rows
for one unscored game. The existing duplicate-exclusion policy, probability tie
rule, fixed holdout and training/calibration checks are unchanged; no earliest or
latest forecast is selected. The published view remains unscored with no eligible
publication ledger, even when historical results exist for the selected season.
