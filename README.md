# March Lab

March Lab explores men's NCAA Division I tournament brackets, probabilities
and historical model evidence. It combines a real main-bracket archive with
interpretable seed models, optional pre-March form features and an interactive
browser app. It is an independent project with no NCAA affiliation.

This is an experimental forecasting and historical-analysis tool. The bundled
predictions were generated retrospectively; **no eligible prospective published
record is bundled**. Historical accuracy does not establish future tournament
performance or the accuracy of a fully filled bracket.

[User guide](docs/USER_GUIDE.md) · [Data provenance](docs/DATA.md) ·
[Model methodology](docs/MODEL.md) · [Track-record rules](docs/TRACK_RECORD.md)

## What you can do

- Browse recorded main brackets, matchup outcomes and available scores/dates.
- Compare actual results, a deterministic model-picked path and a reproducible
  random bracket, with distinct labels for each.
- Inspect numeric matchup and advancement probabilities, historical model
  horizons, calibration and year-by-year evidence.
- Open team tournament profiles, recorded-matchup comparisons and historical
  scouting dossiers with explicit identity and feature-coverage limits.
- Import a locally supplied announced field as an unverified scenario.
- Use keyboard navigation and phone round lists, or a scrollable connected
  bracket on larger screens, in Light, Dark or System theme.

The bundled [2027 configuration](data/field_2027.json) records an unknown field
and a 76-team/12-opening-game structure. It contains no guessed entrants, seeds
or opening placements. Consult its linked official source and validate the real
announced field before importing it. Imported scenarios use the current seed
snapshot; labeling one with an older year does not make it a historical as-of
forecast. See [FIELD_FORMAT.md](docs/FIELD_FORMAT.md).

## Getting started

Use Python **3.11+** (CI uses **3.12**). No Node packages, provider key, Kaggle
account or paid service is required to run the app. Bundled archives, derived
features and trained artifacts work offline after dependency installation.

```bash
git clone https://github.com/roni-altshuler/march_madness_predictor.git
cd march_madness_predictor
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m madness serve
```

Open `http://127.0.0.1:8027`. The server binds to localhost. On Windows, activate
with `.venv\Scripts\Activate.ps1`, or use `.venv\Scripts\python.exe` directly.
No `.env` configuration is required for the bundled app.

## Architecture and repository map

```text
madness/           Archive parsing, features, models, evaluation, brackets,
                   local HTTP server and static exporter
web/               HTML, CSS and browser modules; no frontend build toolchain
data/archive/      Pinned historical source files
data/derived/      Labels, features, identities, coverage and provenance hashes
data/field_2027.json  Unknown-field metadata and structural requirements
artifacts/         Trained models, historical snapshots, predictions and evaluation
licenses/          Third-party source license texts
tests/             Python, parity, source-integrity and browser regressions
docs/              Data/model/field guides, release and verification evidence
.github/workflows/ Verification and GitHub Pages publication
```

Python produces probabilities and evaluates the models. The local API and
static export share those artifacts. The browser reads probability tables,
aggregates valid bracket paths and draws brackets; it does not fit a second
model. Raw schedule caches, private/user imports and generated `public/` output
are ignored.

## Coverage and data provenance

| Layer | Bundled coverage | Limits |
| --- | --- | --- |
| Main-bracket archive | 41 tournaments, 1985–2026 excluding cancelled 2020; 2,583 advancements | 1939–1984, preliminary games and preliminary losers absent. |
| Played labels | 2,582 games | Oregon–VCU 2021 is a no-contest advancement, excluded from fitting and scoring. |
| Scores and UTC dates | 1,259 played main-bracket games, 2006–2026 excluding 2020 | Earlier score/date enrichment and venues absent. |
| Pre-March features | 64 main-bracket teams in each of 20 modern seasons | No pre-2006 form features; not complete NCAA regular-season coverage. |
| Team profiles | Verified modern per-season ESPN IDs and separate older archive-key records | No inferred complete-career joins, player stats, rosters or qualification model. |
| 2027 | Structural metadata; unknown field | No actual entrants or prospective outcomes. |

The archive is from [possibly-wrong/ncaa-tournament](https://github.com/possibly-wrong/ncaa-tournament),
pinned at `036bc619ab30705476da9a420279c4d177365e7d`, under the Unlicense.
Modern schedules are from **SportsDataverse hoopR-mbb-data authors**, upstream
ESPN, under **CC BY 4.0**. Adaptations produce pre-March features and
cross-validated scores/results. [DATA.md](docs/DATA.md) records attribution,
source URLs, SHA-256 hashes, exact coverage and reviewed name corrections.

Schedules were retrieved retrospectively and can include later provider
corrections. A hash pins the evaluated version; it does not establish an
immutable contemporaneous feed. Similar team names do not establish identity.
Missing and uncrosswalked records remain separate.

## Model and evaluation

The primary model is symmetric ridge-logistic seed prediction. The seed-curve
challenger adds a log-seed ratio; the form challenger adds within-season Elo,
win rate and mean margin frozen at **March 1, 00:00 UTC**, plus selection-time
seeds. It is not a selection-day team-statistics model.

Annual expanding-window evaluation fits only earlier tournaments and calibrates
with earlier out-of-fold predictions. Development covers 1995–2019; the rolling
2021–2026 holdout contains **377 games**. Later holdout years can train on earlier
holdout years. This holdout was inspected during development and is not an
unseen lockbox.

| Forecaster | Brier ↓ | Log loss ↓ | ECE ↓ |
| --- | ---: | ---: | ---: |
| 50/50 | 0.25000 | 0.69315 | 0.00000 |
| Fixed seed heuristic: 75% to better seed | 0.20474 | 0.60011 | 0.03249 |
| **Seed logistic — primary** | **0.19358** | **0.56876** | **0.03484** |
| Seed curve challenger | 0.19072 | 0.56242 | 0.03735 |
| Pre-March form challenger | 0.19392 | 0.56965 | 0.03813 |

All rows score the same 377 games in [evaluation.json](artifacts/evaluation.json).
The curve's small Brier gain has a tournament-cluster bootstrap interval that
includes zero; form does not improve the primary's Brier score here. Neither
challenger is promoted. Only six holdout tournaments limit the evidence.
A calibrated 50/50 baseline can still have no useful discrimination.

The [integer-pick record](docs/TRACK_RECORD.md) is **269/377 (71.4%)**, based on
saved primary probabilities for actual historical matchups. This is separate
from probabilistic scores, prospective accuracy and filled-bracket advancement.
Preliminary survivors are already known in the historical 64-team fields, so
simulations are conditional main-bracket experiments. No injuries, roster or
transfer features, market benchmark or pool-scoring optimization are included.

## Reproduce or update locally

From the activated virtual environment:

```bash
# Inference from bundled artifacts; no network or retraining
python -m madness predict --a 5 --b 12
python -m madness predict --a 5 --b 12 --model seed_curve
python -m madness simulate --year 2026 --rng 42 --output /tmp/march-simulation.json

# Refit and reevaluate from bundled labels/features; rewrites model artifacts
python -m madness train

# Optional source reconstruction/downloads; review resulting provenance changes
python -m madness ingest
python -m madness schedules --start 2006 --end 2026
```

Choose a writable output path instead of `/tmp` on Windows. Downloads are
bounded and checked against recorded hashes. Changed upstream bytes require an
explicit `--refresh-source` and a new evaluation. Do not treat that flag as a
routine way to suppress a source mismatch. No automatic live ingestion schedule
is configured; data/model updates are explicit operations.

A local field import can also be simulated with
`python -m madness simulate --field data/imports/announced_2027.json --rng 42`
after creating a valid field file. Keep user imports out of Git and follow the
[field format](docs/FIELD_FORMAT.md).

## Verification and deployment

Install `requirements-dev.txt` for browser testing. CI uses Node **22** for
JavaScript syntax and Playwright Chromium for the actual app checks:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node --check web/app.js
node --check web/bracket_home.js
node --check web/track_record.js
node --check web/theme.js
node --check web/static_api.js
node --check web/season_insights.js
node --check web/team_profiles.js
node --check web/team_scouting.js
node --check web/matchup_compare.js
python -m playwright install chromium
MARCH_BROWSER_CHANNEL=chromium python tests/browser_check.py
python -m madness export
MARCH_BROWSER_CHANNEL=chromium python tests/browser_check.py --static
```

Set the environment variable with your shell's equivalent syntax on Windows.
No separate lint/type-checker or Node build is configured. The
[verification workflow](.github/workflows/verify.yml) also checks CLI inference
and simulation. [VERIFICATION.md](docs/VERIFICATION.md) describes coverage,
responsive/keyboard journeys and dated results.

`python -m madness export` builds ignored `public/`, which works under a project
subpath without a Python backend. Preview it with
`python -m http.server 8028 --bind 127.0.0.1 --directory public`.
[The Pages workflow](.github/workflows/pages.yml) runs tests and exports before
publication on main. Verify the deployed source revision and actual app at
phone, tablet and desktop sizes after any deployment. The
[release record](docs/RELEASE.md) documents the original release; it is not a
current deployment guarantee.

## Contributions, security and license

Follow [AGENTS.md](AGENTS.md) when changing the repository. Keep chronological
boundaries, baselines, source hashes and Python/static parity intact. Submit
focused pull requests with reproduction and validation evidence. Do not commit
Kaggle data, raw schedule caches, credentials or private imports.

Use GitHub private vulnerability reporting if enabled for security issues;
avoid sensitive payloads in public issues. Treat imported files as untrusted
and retain localhost binding for development.

Project code is licensed under [MIT](LICENSE). Source data retains its original
terms, preserved in [licenses/](licenses/) and [DATA.md](docs/DATA.md). The code
license does not replace required data attribution. Estimates support
exploration and evaluation, not betting advice.
