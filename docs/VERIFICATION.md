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

## Not run or unavailable

- Prospective 2027 accuracy: no games or announced field exist yet.
- Full-field historical Opening/First Four evaluation: those games are absent.
- Injury/roster/market benchmarks and pre-2006 form evaluation: data unavailable.
- Safari/iOS/Android device testing: not run; viewport checks use desktop Edge.
- Full 1939–1984 archive: not ingested, explicitly missing.

Passing tests establish the
tested behavior and temporal safeguards, not guaranteed future prediction skill.
