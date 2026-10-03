# First-release verification

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
historical simulation, plus Chromium browser checks on Ubuntu. Remote status
will be verified before merging the first-release PR. A separate release record
and the final report identify the actual PR, CI run and merged commit.

Review covers temporal boundaries, source identities/provenance/licensing,
unmatched data behavior, declared bracket validation, untrusted import escaping,
responsive/keyboard UI and absence of credentials/raw private data from Git.

## Not run or unavailable

- Prospective 2027 accuracy: no games or announced field exist yet.
- Full-field historical Opening/First Four evaluation: those games are absent.
- Injury/roster/market benchmarks and pre-2006 form evaluation: data unavailable.
- Safari/iOS/Android device testing: not run; viewport checks use desktop Edge.
- Public publication: newly user-authorized, pending release PR review/CI and
  the separately recorded verification of the resulting live page.
- Full 1939–1984 archive: not ingested, explicitly missing.

No local failed checks remain at this checkpoint. Passing tests establish the
tested behavior and temporal safeguards, not guaranteed future prediction skill.
