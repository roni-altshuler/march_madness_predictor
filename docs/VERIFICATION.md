# Verification history

Date: 2026-10-03. Local environment: Windows (YogaRoni), Python 3.12, NumPy 2.3.3,
PyArrow 21.0.0, pytest 8.4.2, Playwright 1.55.0 and installed Microsoft Edge.
The project is isolated in `task-2/march_madness_predictor`; sibling repositories
are not changed.

## Passed locally

- `python -m pytest -q`: 27 tests passed. Archive tree/counts, immutable source
  hashes, no-contest exclusion, probability symmetry and seed order, invalid
  seeds, strictly earlier coefficient/calibration seasons, future-label isolation,
  metric recomputation, feature coverage/horizons, corrected team identities,
  modern score cross-validation, bracket probability mass, valid seeded winner
  flow, 76-team/12-opening-game structure and malformed/unknown field rejection.
  Static seed/form tables match Python, and browser/Python bracket odds and
  seeded draws agree for all three models and a 76-team structural fixture.
- `node --check web/app.js`: JavaScript syntax passed.
- `python tests/browser_check.py`: actual Edge 1440px desktop, 768px tablet and 390px mobile checks
  passed. Year/region navigation, matchup modal, Enter/Escape/focus restoration,
  form-model comparison, real score provenance, actual and simulated brackets,
  2021 no-contest, 1985 warm-up, equal-seed matchup, evidence/calibration page,
  unknown 2027 field, invalid import and a valid in-memory 76-team structural
  import were exercised. No JavaScript page errors; no document-wide mobile
  overflow. Mobile shows one readable round list selected by a native control. Synthetic structural fixtures are test-only and never stored as
  real tournament data.
- `python tests/browser_check.py --static`: the same browser workflow passes on
  the exported app served without a Python API. Public assets use relative paths.
- CLI inference: 5 versus 12, prospective model through 2026, returned
  `P(seed 5 wins) = 0.7553902159981174`.
- CLI historical simulation: 2026, RNG 42, 64 main-bracket participants and
  63 games. Exact advancement probability mass and monotone winner flow pass.
- Independent modern result checks: all 1,259 played main-bracket games from
  20 seasons (2006–2026 excluding 2020) match SportsDataverse/ESPN winners.
- Trained artifacts: 2,582 seed labels; 1,259 form labels; 377 chronological
  rolling holdout games, 2021–2026. Holdout Brier/log loss: seed
  0.1935790/0.5687618; fixed seed heuristic 0.2047414/0.6001146; seed curve
  0.1907181/0.5624247; form 0.1939190/0.56965 (full precision in evaluation JSON).
- Desktop landing/bracket and mobile bracket screenshots were captured and
  visually inspected in `docs/screenshots/`. Connectors, typography, layout,
  legibility, desktop/tablet bracket scrolling and mobile round lists were checked.

The score and form mapping audit found and corrected two ambiguous community
labels before final evaluation. The form model is slightly worse than the seed
baseline after correction. It is not promoted. Curve/form paired confidence
intervals include zero; only six holdout tournaments limit the evidence.

## CI and release review

The GitHub workflow runs backend checks, JavaScript syntax, CLI inference and
historical simulation, plus Chromium browser checks on Ubuntu. The first-release
PR was reviewed and merged after both CI runs passed. Main verification and
GitHub Pages publication passed. The actual public app was verified in Edge,
including its project subpath, historical bracket, modal, simulation, unknown
2027 field and mobile navigation. [RELEASE.md](RELEASE.md) records the URLs,
review, CI runs and merged implementation commit.

The browser regression workflow also checks keyboard activation of Skip to
content on the archive, its simulated view and the mobile round list. Focus must
move to the main landmark while the route, year and rendered state stay intact.
This regression failed on the first release because the URL changed from
`#archive` to `#main`; it passed locally after the skip link received a dedicated
focus/scroll handler that prevents the hash navigation.

Review covers temporal boundaries, source identities/provenance/licensing,
unmatched data behavior, declared bracket validation, untrusted import escaping,
responsive/keyboard UI and absence of credentials/raw private data from Git.

## Season evidence inspector · 2026-10-06

Verified in the saved Linux cloud workspace, starting from main
`fae9ffa92b7a1b1b01d60148c005b535a2128558`. No open PR was reported by the
GitHub connector before this follow-on work. The unpublished laptop-only
`feat/cbs-bracket` commit `e2b0e2e` was unavailable and was not recovered.
This change adds a separate evidence inspector; it does not replace the bracket.

- Python suite: 27 tests passed. Syntax checks passed for `web/app.js`,
  `web/static_api.js` and `web/season_insights.js`.
- Static export, CLI seed inference and the 2026 historical simulation passed.
- Playwright Chromium checks passed against both the local API app and exported
  static app. They exercise 1985 warm-up dashes, absent 1995 scores/form and
  calibration fit, 2006 form coverage without an eligible model, 2008 form model
  availability, 2021 no-contest exclusion, cancelled 2020 and exact saved 2026
  training/calibration counts and seed Brier score.
- Desktop and phone views were inspected visually. At 390px, all four score
  columns fit; at 320px, keyboard scrolling keeps overflow inside the table.
  The archive action preserves the selected year when activated with Enter.
- Delayed-request and failed-request regressions passed: a late response cannot
  replace the newly selected year; a failed request clears old evidence and a
  retry restores the requested season.
- `agent-browser` verified the local page and static export under
  `/march_madness_predictor/`: content, controls and navigation loaded with no
  JavaScript errors. Chromium needed a temporary writable Fontconfig cache and
  TrueType fallback configuration in `/tmp` because this cloud image's default
  WOFF2 system-font fallback rendered zero-height text. This environment setup
  is not part of the app or repository.

Inspector screenshots: [desktop](screenshots/season-evidence-desktop.png) and
[mobile](screenshots/season-evidence-mobile.png). Data sources, saved model
artifacts, the primary seed model and existing bracket behavior are unchanged.
No training, model promotion, merge or production job was performed.

The follow-on visual pass applies cream (`#f3f0e7`) and warm neutral surfaces only
to this inspector, preserving the dark shell and existing bracket. Main text,
muted text and the bracket action measured 13.54:1, 5.43:1 and 7.34:1 contrast
respectively against their actual backgrounds. No new surface is pure white.
The browser workflow now also verifies Back/Forward navigation after the bracket
action, keyboard retry, explicit busy/loading presentation and zero control
transition duration when reduced motion is requested. Transient HTTP 503 errors
in the static loader are distinguished from absent HTTP 404 snapshots.

Desktop and mobile [loading](screenshots/season-evidence-loading-desktop.png),
[cancelled](screenshots/season-evidence-cancelled-desktop.png) and
[error](screenshots/season-evidence-error-desktop.png) screenshots are captured
alongside the populated view. Mobile state counterparts use the `-mobile.png`
suffix. [Desktop page context](screenshots/season-evidence-page-desktop.png) and
[mobile page context](screenshots/season-evidence-page-mobile.png) show the
inspector within the preserved March Lab identity.

## Team tournament profiles · 2026-10-06

This bounded follow-on starts from main `143fd4db729e45a2365e3955f9314d5257d46b5a`.
No open PR was reported before starting. The profile journey adds links inside
historical matchup details and preserves the existing bracket renderer.

- Python suite: 35 tests passed. New checks separate the reused `SanDiego` and
  `Lafayette` labels and similarly named Miami teams, reject same-tournament
  identity collisions, allow a changed archive name only with an agreeing
  published ID, and keep older uncrosswalked Duke records separate.
- Totals independently reconcile to the archive: 2,624 appearances, 2,582 played
  wins, 2,582 played losses, 41 titles, two team no-contest entries and one
  no-contest advancement. Cancelled 2020 cannot create an appearance.
- Exported profiles match local API state exactly. Hash-based filenames and
  exact index membership prevent guessed, inherited or traversal-like profile
  IDs from resolving to a record. Source archive/features are not mutated.
- JavaScript syntax checks cover the app, static API, season inspector and new
  profile module. Static export uses the existing published artifacts only.
- Actual Chromium browser checks cover local API and static modes, desktop,
  768px tablet, 390px phone and 320px narrow views. They exercise game → team →
  appearance → bracket navigation, origin year/region/game/round focus, browser
  Back/Forward, an unchanged sampled draw, old/modern identity boundaries,
  opponent links, no-contest outcomes, cancelled and other missing years,
  unavailable IDs, keyboard retry, stale responses and reduced motion.
- Results and appearance tables keep overflow inside focusable regions and
  support keyboard scrolling. Original cream/navy surfaces and text initials
  retain the dark March Lab shell; no official portraits/logos or new assets
  were sourced. Desktop/mobile screenshots were visually inspected.
- `agent-browser` independently exercised the mobile no-contest journey and
  static profiles under `/march_madness_predictor/`, including selecting a past
  appearance and returning to the origin year. No JavaScript errors appeared.

Profile screenshots: [desktop](screenshots/team-profile-desktop.png),
[mobile](screenshots/team-profile-mobile.png),
[no-contest](screenshots/team-profile-no-contest-desktop.png),
[cancelled appearance](screenshots/team-profile-cancelled-desktop.png), and
[unavailable ID](screenshots/team-profile-unavailable-mobile.png).
This change does not alter model artifacts, ingest data, retrain, merge or
dispatch publication. Public live verification of this draft is not claimed.

Independent navigation review reproduced three failures: a recorded 2026 link
kept a sampled view, control changes left a stale archive hash for browser Back,
and a delayed simulation raised a page error and changed the return view. A
related cross-year journey also lost the original draw. Focused fixes make
archive views explicit, replace the current URL as controls/game selections
change, retain the latest draw per year in memory and discard simulation
successes or failures after the requesting route/year is no longer current.

Actual local/static Chromium regressions use the existing field/artifacts with
RNG 42. They check sampled 2026 → profile → recorded 2026 as actual results;
2026 → profile → 2015 → Back → Back as the exact original 2026 sampled draw;
changed 2021/Region 3 controls → profile → browser Back/Forward on desktop and
phone; and intercepted delayed simulation success/failure responses while a
profile is open. The profile DOM stays unchanged, its return stays actual and
no JavaScript errors occur. Reload clears ephemeral draws and canonicalizes the
URL and visible label to actual results. No production endpoint is used.

## Recorded matchup comparison · 2026-10-07

Started from main `5f52fed75edb7a435d322ebfa0eb11fb0b71cffa`; no open PR was
reported before work. The audit found a native JavaScript/CSS app with no Node
UI package dependencies. The existing seed lab, detail model selector, annual
evidence inspector, history links, API and static tables were reused. The
unpublished laptop CBS rewrite remains untransferred and was not recovered.

Story: actual game details → Matchup Lab year/game controls → saved annual season
and prediction artifacts → paired model cards → existing history/evidence/actual
bracket links. No dataset, model artifact or training code changes.

| Boundary | Verified evidence |
|---|---|
| Browser → data | Native year/game controls request existing `/api/season` and `/api/predict`; static mode reads the existing relative season/model tables |
| Data → probabilities | 45 Python/Node checks pass; comparison values match Python predictions for the same recorded game, swapped sides complement, percentage-point gaps reverse and horizons precede the selected tournament |
| Missing data | 1985 renders three dashed snapshots; 2006 has form features without a trained form model; Oregon–VCU has no played-game probabilities; cancelled 2020 has no matchup/model cards |
| Response → browser | Actual Chromium interactions pass in local/static modes at desktop, tablet, 390px and 320px, with no document overflow or JavaScript page errors |

Browser interactions include Enter from an actual matchup into the comparison,
focus on its year control, repeated game selection, keyboard side swapping with
focus retained, team-history and evidence links, and Back/Forward returning to
the selected game and explicit actual bracket. The 2026 final displays UConn
46.1% under the primary seed snapshot, 39.9% under the curve and 37.6% under form;
all train through 2025. Swapping sides shows the complementary probabilities and
reversed signed gaps. The comparison does not promote a challenger.

Controlled local HTTP fixtures verify busy/loading, an empty cancelled year, a
503 error and Enter retry. Delayed season and prediction/table responses cannot
replace the newer selection or resurrect a departed route. The delayed 2008
comparison resolves to the selected equal-seed final with 50% under both seed
models, rather than the earlier first-round values. Reduced motion produces zero
control-transition duration. Source fixtures are not edited or newly collected.

Desktop/mobile populated, warm-up, no-contest, loading, empty and error
screenshots were captured and visually inspected. The original cream/navy cards
reuse the evidence palette, native controls and dark March Lab shell. No new
logos, portraits, paid services, providers, credentials or access settings were
introduced. Actual browser QA also covers the exported app under the project
subpath `/march_madness_predictor/`; build/DOM checks alone are not used as proof.

[Desktop](screenshots/matchup-comparison-populated-desktop.png) ·
[Mobile](screenshots/matchup-comparison-populated-mobile.png) ·
[Loading](screenshots/matchup-comparison-loading-mobile.png) ·
[Cancelled/empty](screenshots/matchup-comparison-empty-mobile.png) ·
[Error](screenshots/matchup-comparison-error-mobile.png).
All JavaScript syntax checks and static export pass. No production workflow was
manually dispatched or merged; the draft requires independent review.

### Independent review follow-up

Targeted actual Chromium QA on the reviewed head `ed73a8adf63ecda8a22403668a721892e17e16c3`
found one control-state mismatch: after swapping sides, selecting cancelled 2020
cleared the URL's side parameter and all game cards but left the disabled swap
button's `aria-pressed` state true. Loading now synchronizes that state and year
changes reset the side. Saved probabilities and model chronology are unchanged.

The fix passes targeted API/static checks at 1440px desktop and 390px mobile.
Each case performs 40 rapid real button activations and 19 game changes, checks
both teams' displayed probabilities against the existing Python artifacts, and
asserts year/game/side agreement across the URL, controls and content. Cancelled
2020 → season evidence → Back returns the same cancelled state with disabled
controls, no game/side URL parameters and no forecast cards. Changing a team
history's appearance year and going Back preserves the comparison's selected
game and swapped orientation. The profile's explicit bracket return preserves
the actual championship, final-round selection and keyboard focus.

Delayed prediction responses are released in reverse request order after rapid
game changes; the 2008 final remains selected with 50% under both seed models.
A late season response released after cancelled-year evidence/Back cannot replace
2020. All four combinations pass with no page errors or document overflow.
The normal browser suite also guards cancelled evidence/Back, rapid swaps and
game changes, and the swap reset during loading. Screenshots were visually
inspected; no deployment or access changes were made.

[Cancelled Back · desktop](screenshots/matchup-comparison-review-cancelled-back-desktop.png) ·
[mobile](screenshots/matchup-comparison-review-cancelled-back-mobile.png) ·
[History Back · desktop](screenshots/matchup-comparison-review-history-back-desktop.png) ·
[mobile](screenshots/matchup-comparison-review-history-back-mobile.png).

## Historical team scouting dossier · 2026-10-08

Started from merged main `ac95e07c2e54e846f7f0c9bb26902de7503e367c` after checking
that no PR was open. The saved cloud checkout was clean. Root `.agents`/`.codex`
had no extra skill/instruction files; the repository's men's-only, chronological
model and exact-identity rules remain in force. The laptop CBS rewrite remains
unavailable and untouched. No bracket rewrite, source collection or training.

Story: recorded bracket/matchup → existing team profile → frozen form and saved
annual seed probabilities → selectable earlier-appearance window → source matchup
comparison and return navigation. The existing `/api/team` and exported profile
JSON carry display-only form context and paired game probabilities. No new
endpoint, provider, dependency or access setting is needed.

| Boundary | Evidence |
|---|---|
| Data → probabilities | 57 Python/Node tests pass. Displayed earlier expectations match the seed model on identical played game IDs, in each team's orientation. Every saved model fits strictly before its own tournament |
| Temporal window | Last 3/5/all windows include appearances strictly before the selected year. Changing selected/later outcomes cannot change the earlier summary. Old archive keys are not joined into modern ESPN identities |
| Form → field context | Finite Elo/win-rate/margin values at March 1, 00:00 UTC, compared only with covered archived entrants at the same cutoff. Percentile = 100 × (lower values + half tied values) / covered values |
| Missing data | No-contests excluded; warm-up expectations and missing form are dashes. First modern appearance has no earlier identity record. Cancelled 2020 and unrecorded 2027 have no dossier forecasts or scouting controls |
| Browser → API/static → UI | Actual Chromium desktop/mobile interactions, keyboard controls, loading/error/retry, repeated navigation and delayed profile responses are covered in `tests/scouting_browser.py`, called by the full browser suite |

Duke's five recorded appearances before 2026 are 2025, 2024, 2023, 2022 and 2019:
20 covered played games, 15 recorded wins, 13.53 expected wins under their own
earlier-trained seed snapshots and a +1.47 difference. These are sums on the
opponents actually faced, not expected full-bracket wins. The form panel shows
29 covered games, Elo 1694.9, win rate 93.1% and mean margin 20.3 points, with
field percentiles 96.1, 94.5 and 96.1 among 64 covered archived entrants. This
field is conditional on preliminary survivors, not a selection-day full field.

Controls preserve lookback/year in the URL across reload and Back/Forward; Enter
from an earlier row opens Duke's real `2025-r1-16` matchup. Returning to the
origin bracket restores 2026, its region/round and game focus. A delayed Duke
profile cannot overwrite a newer Michigan profile. Retry with Enter preserves
the requested lookback. Reduced motion disables control transitions; table
scrolling remains keyboard accessible on mobile. No confidence interval, player
value, team ability ranking or prospective accuracy claim is introduced. The
seed baseline and rolling holdouts do not consume this display-only dossier.

Full API and static browser suites pass. The dossier flow also passes under the
exported project's `/march_madness_predictor/` subpath at desktop 1440×1000 and
mobile 390×844; 768px and 320px checks have no document overflow. All twelve
populated/no-prior/warm-up/loading/error/cancelled screenshots were captured and
visually inspected at both sizes. Six JavaScript syntax checks, static export and
whitespace checks pass. No separate lint or TypeScript configuration exists in
this native JavaScript/Python app. Source `data` tree
`54b8d1b74c96a76390d7edf4469b363abd00b0d1` and model `artifacts` tree
`641b4a61c6872c384fe810f9befe9b5815316ad3` remain unchanged. No merge or manual
production workflow dispatch; independent review is required before shipping.

### Reel reference and reuse decision

Reviewed `grandngom/xG-model-football` at commit
`c992f0335ddecc281c211dda062132808868fb3f` on 2026-10-08. Its
[license](https://github.com/grandngom/xG-model-football/blob/c992f0335ddecc281c211dda062132808868fb3f/LICENSE)
is MIT; its [README](https://github.com/grandngom/xG-model-football/blob/c992f0335ddecc281c211dda062132808868fb3f/README.md)
reports 50 soccer matches, 1,390 shots and 166 goals. Its
[main script](https://github.com/grandngom/xG-model-football/blob/c992f0335ddecc281c211dda062132808868fb3f/main.py)
uses shot geometry/context, random shot splits and evaluates/bootstrap-samples
full-dataset predictions that include training shots. This is not evidence for
chronological basketball validation or a production tournament model. No code,
soccer data or fitted models were copied; the other reel's gated bundle was not
obtained. The useful expected-versus-observed comparison idea is implemented in
the correct unit—played tournament wins—using the existing NumPy model and
native accessible UI. Existing basketball provenance and source licenses remain
unchanged.

[Desktop dossier](screenshots/team-scouting-populated-desktop.png) ·
[Mobile dossier](screenshots/team-scouting-populated-mobile.png) ·
[No earlier identity](screenshots/team-scouting-no-prior-mobile.png) ·
[Warm-up](screenshots/team-scouting-warm-up-mobile.png) ·
[Loading](screenshots/team-scouting-loading-mobile.png) ·
[Error](screenshots/team-scouting-error-mobile.png).

## Not run or unavailable

- Prospective 2027 accuracy: no games or announced field exist yet.
- Full-field historical Opening/First Four evaluation: those games are absent.
- Injury/roster/market benchmarks and pre-2006 form evaluation: data unavailable.
- Safari/iOS/Android device testing: not run; viewport checks use desktop Edge.
- Full 1939–1984 archive: not ingested, explicitly missing.

Passing tests establish the
tested behavior and temporal safeguards, not guaranteed future prediction skill.
