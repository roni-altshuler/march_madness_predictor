# Declared field format

The checked-in `data/field_2027.json` deliberately has status `unknown` and no
teams. It cannot be simulated. Import the real announced field to produce odds.
The imported field remains in memory in the browser/API; the server does not
write uploads. Store CLI inputs under ignored `data/imports/` if desired.

Required JSON keys: `season`, `status`, `expected_teams`,
`expected_opening_games`, `slots`. The 2027 counts are 76 and 12.

`slots` is a list of 64 lists. Each list contains one team or two teams that
play an opening game for that main-bracket slot. Each team has a unique string
`id`, a display `name` and an integer `seed` from 1 to 16. An opening pair shares
the seed of its destination slot. The UI validates JSON under 100 KB.

Four consecutive groups of 16 slots form the regions, in official semifinal
pairing order: regions 1/2 feed one semifinal, regions 3/4 the other. Every
region uses seed order:

```
1,16,8,9,4,13,5,12,2,15,7,10,3,14,6,11
```

An abbreviated schema, **not a valid fixture or tournament**:

```json
{
  "season": 2027,
  "status": "announced",
  "expected_teams": 76,
  "expected_opening_games": 12,
  "slots": [
    [{"id": "actual-team-id", "name": "Actual team", "seed": 1}]
  ]
}
```

Fill all 64 slots from the real bracket. The simulator accepts a generic
declared 64-slot structure with opening pairs for other eras; 2027 specifically
requires 12 pairs. It does not guess the committee's opening-game placements.
N participants require N−1 eliminations: 76 teams imply 75 played games if no
game is cancelled/no-contest. Historical source experiments use 64 main-bracket
teams and 63 advancements, with Oregon–VCU 2021 excluded from played labels.

The field import is a user-supplied scenario, not a trusted NCAA feed. It never
changes the committed unknown field. Structural test fixtures use explicitly
test-only IDs and are never published as actual 2027 entrants.
