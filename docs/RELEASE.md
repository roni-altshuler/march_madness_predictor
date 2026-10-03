# Public release record

Verified 3 October 2026. Independent men's NCAA Division I project for Roni
Altshuler; no NCAA affiliation. The repository and free GitHub Pages publication
were explicitly authorized.

- [Public app](https://roni-altshuler.github.io/march_madness_predictor/)
- [Repository](https://github.com/roni-altshuler/march_madness_predictor)
- [First release PR #1](https://github.com/roni-altshuler/march_madness_predictor/pull/1)
- [Recorded engineering review](https://github.com/roni-altshuler/march_madness_predictor/pull/1#pullrequestreview-5400632304)
- Merged implementation commit: `31c3d9fe43c20e5df42d0f51fe8d53add499dda1`.

## Confirmed checks

Both PR [verification run 37121175899](https://github.com/roni-altshuler/march_madness_predictor/actions/runs/37121175899)
and [run 37121136277](https://github.com/roni-altshuler/march_madness_predictor/actions/runs/37121136277)
passed. After merge, [main verification](https://github.com/roni-altshuler/march_madness_predictor/actions/runs/37121521060)
and [Pages publication](https://github.com/roni-altshuler/march_madness_predictor/actions/runs/37121521076)
passed. The published page returned HTTP 200 and actual Edge checks exercised
the unknown 2027 field, 2026 archive, matchup details, bracket simulation,
390px round list and matchup probabilities without JavaScript errors or
document-wide overflow. A screenshot of that real app is the portfolio preview.

Local release checks passed: 27 Python tests, JavaScript syntax, CLI inference
and simulation, reproducible training, and API/static browser workflows at
1440px, 768px and 390px. Tests cover temporal boundaries, immutable source
hashes, no-contest handling, team mappings, score validation, valid bracket
paths and Python/browser probability and seeded-draw parity.
The [verification document](VERIFICATION.md) gives the full scope and limits.

## Coverage and measured evidence

The archive contains 41 main brackets from 1985 through 2026, excluding cancelled
2020: 2,583 advancements and 2,582 played games. Oregon–VCU 2021 is a no-contest.
The 1939–1984 archive and preliminary/First Four games and losers are absent.
Scores/dates and pre-March features cover 20 modern seasons from 2006 through
2026 excluding 2020; all 1,259 played main-bracket results were cross-validated.
This is not complete coverage of every previous tournament or of every NCAA
regular-season game. Archive and feature coverage are separate.

The trained primary seed model's 377-game retrospective rolling holdout
(2021–2026) has Brier 0.1935790, log loss 0.5687618 and ECE 0.0348431. The fixed
seed heuristic has Brier 0.2047414. The curve challenger has Brier 0.1907181;
the form challenger has Brier 0.1939190. Neither challenger is promoted: their
paired tournament-bootstrap intervals include zero, and the form model is
slightly worse than primary. Only six holdout tournaments limit the evidence.
Primary and fixed-heuristic winner-pick accuracy are the same, about 71.4%.
The measured improvement is in probability scoring, not winner-pick accuracy.
There is no prospective accuracy claim. [MODEL.md](MODEL.md) and the committed
evaluation artifact explain the chronological fitting/calibration protocol.

The 2027 entrants, seeds and opening assignments are unannounced. The app
publishes dates and format, and accepts a validated user-imported field when
available. No fictional 2027 fixtures are included. Historical simulation is
conditional on known main-bracket participants after preliminary games.

## Data and publication

The archive is Unlicense; SportsDataverse schedule adaptations retain CC BY 4.0
attribution. [DATA.md](DATA.md) records provenance, source versions, hashes,
measured coverage and corrected identities. Code is MIT. Raw schedule caches,
private imports, credentials and generated static output are ignored. Static
publication uses Python-computed probability tables and valid bracket
aggregation; it requires no paid backend or new account.
