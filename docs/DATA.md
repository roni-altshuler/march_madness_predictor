# Data provenance and coverage

Retrieval date: 2026-10-03. This project distinguishes the tournament archive
from the feature era. More old games are not a guarantee of better prediction.

## Main-bracket source

Repository: https://github.com/possibly-wrong/ncaa-tournament
Pinned commit: `036bc619ab30705476da9a420279c4d177365e7d`.
License verified in that checkout: Unlicense. Original text is preserved at
`licenses/possibly-wrong-Unlicense.txt`.

41 yearly files are bundled unchanged: 1985–2026, excluding cancelled 2020.
Each has 64 ordered team/seed/win rows. A tree is reconstructed by repeatedly
pairing adjacent participants and advancing the unique team whose main-bracket
win count reaches that round. Each region's seeds, uniqueness, per-round counts,
winner flow and sum of win counts are checked. SHA-256 hashes are recorded in
`data/derived/provenance.json`; `.gitattributes` preserves source bytes.

The source is community maintained, not an official NCAA feed. Labels are
preserved as IDs but modern display names are mapped to the schedule publisher.
Two reviewed season-specific corrections are necessary: `Lafayette` identifies
Louisiana in the 2023 source bracket; `SanDiego` identifies UC San Diego in 2025,
whereas San Diego in earlier tournaments is a different university. Exact,
reviewed aliases are in `madness/schedules.py`; no fuzzy matches are used.

The archive contains 2,583 advancements, with 2,582 played labels. The March 20,
2021 Oregon–VCU game was declared a no-contest: Oregon's advancement is shown,
and that event is excluded from both model fitting and scoring. Win totals
are outcomes used to reconstruct labels, never predictor features.

## Modern schedules

Publisher: SportsDataverse hoopR-mbb-data authors; upstream ESPN.
Publisher license statement:
https://github.com/sportsdataverse/hoopR-mbb-data/blob/main/LICENSE.md
CC BY 4.0: https://creativecommons.org/licenses/by/4.0/
Release: https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_mens_college_basketball_schedules
Pattern: `mbb_schedule_YEAR.parquet`.

Twenty schedules are ingested: 2006–2026 excluding 2020. They total 116,124
schedule rows, with 102,645 completed, non-tied games before each year's March 1
00:00 UTC cutoff. All 64 main-bracket participants in each ingested season have
at least ten earlier completed games and an unambiguous reviewed identity map.
This does **not** establish complete coverage of all NCAA regular-season games.
The measured per-season counts, source URLs and file SHA-256 hashes are in
`data/derived/schedule_coverage.json`. Raw caches total approximately 15 MB and
are excluded from Git. Downloads require no credentials or data agreement.

Changes: schedules are adapted into within-season Elo, win rate and mean scoring
margin. Numeric features use only games before the cutoff. Identity metadata is
also taken from before the cutoff. We independently match each modern archived
pair to an NCAA-labeled schedule game and verify the winner. All 1,259 played
main-bracket results from these seasons match; scores and UTC dates are added.
The no-contest gets no fabricated score. A source winner disagreement stops
ingestion. SportsDataverse-derived data retains CC BY 4.0 attribution.

Historical schedules are retrieved retrospectively. Results were available by
the game date, but upstream corrections can postdate a historical prediction.
There is no claim of an immutable contemporaneous feature feed. The files are
hashed and derived artifacts preserve the evaluated version. Re-downloads check
known hashes; an upstream revision requires explicit `--refresh-source` and a
new evaluation rather than silently overwriting the measured source version.

## Missing and structural facts

- 1939–1984: not ingested; no invented archive entries.
- 2020: tournament cancelled, not treated as ordinary missing data.
- Pre-2006: no model-ready regular-season form features or score/date enrichment.
- Opening/First Four games and preliminary-round losers: absent from the archive.
- Geographic region names and venues: absent. Region numbers preserve source order.
- Injuries, roster/transfer changes, detailed box statistics and market odds: absent.
- 2027: actual field unknown. No model forecasts qualification or the committee's seeds.

The historical field grew from 64 in 1985 to 65 in 2001 and 68 in 2011.
The official 2027 schedule states 76 teams and 12 Opening Round games feeding
the main 64. The simulator reads declared slot pairs and semifinal pairing
order instead of assigning future entrants or inventing opening placements.

Official reference pages:

- [NCAA tournament history](https://www.ncaa.com/news/basketball-men/article/2020-06-04/march-madness-history-and-origins)
- [2027 men's schedule](https://www.ncaa.com/news/basketball-men/article/2026-05-07/2027-march-madness-mens-ncaa-tournament-schedule-dates)
- [2020 championships cancelled](https://www.ncaa.com/news/basketball-men/article/2020-03-12/ncaa-cancels-remaining-winter-and-spring-championships)

Some NCAA pages require browser verification; the supplied official date/format
research is preserved in `data/field_2027.json`. Community labels and the modern
schedule-derived results are cross-checked locally. There is no claim that this
is a complete official NCAA historical database.

## Kaggle

Kaggle was not needed or imported. Its competition rules can combine a license
label with additional access and redistribution restrictions; this project does
not assume that a copied public CSV is freely redistributable. A future
user-authorized importer must keep actual Kaggle files under ignored
`data/private/`, document the accepted source terms and information horizon, and
run a separate evaluation. Do not publish those files by default, even privately.
