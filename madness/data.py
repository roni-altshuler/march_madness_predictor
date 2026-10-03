"""Pinned archive ingestion. Outcomes are labels, never model features."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_COMMIT = "036bc619ab30705476da9a420279c4d177365e7d"
ARCHIVE_URL = "https://github.com/possibly-wrong/ncaa-tournament"
ROUNDS = ["Round of 64", "Round of 32", "Sweet 16", "Elite Eight", "Final Four", "Championship"]


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline='\n')


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ingest_archive(persist=True):
    seasons, all_games, hashes = {}, [], {}
    for path in sorted((ROOT / "data/archive").glob("*.txt")):
        year = int(path.stem)
        assert year != 2020, "2020 tournament was cancelled"
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        teams = []
        for i, line in enumerate(path.read_text().splitlines()):
            name, seed, wins = line.split()
            teams.append(dict(id=name, name=name, seed=int(seed), wins=int(wins), slot=i))
        assert len(teams) == 64 and len({t['id'] for t in teams}) == 64
        for start in range(0, 64, 16):
            assert sorted(t['seed'] for t in teams[start:start+16]) == list(range(1, 17))
        games, active = [], teams
        for round_index, round_name in enumerate(ROUNDS, 1):
            next_round = []
            for index in range(0, len(active), 2):
                a, b = active[index:index+2]
                winners = [t for t in (a, b) if t['wins'] >= round_index]
                assert len(winners) == 1, (year, round_index, a, b)
                winner = winners[0]
                no_contest = year == 2021 and {a['id'], b['id']} == {'Oregon', 'VACommonwealth'}
                game = dict(id=f"{year}-r{round_index}-{index//2}", season=year,
                            round=round_index, round_name=round_name, a=a['id'], b=b['id'],
                            seed_a=a['seed'], seed_b=b['seed'], winner=winner['id'],
                            status="no_contest" if no_contest else "played", score_a=None, score_b=None)
                games.append(game)
                next_round.append(winner)
            active = next_round
        assert sum(t['wins'] for t in teams) == 63
        seasons[str(year)] = dict(season=year, teams=teams, games=games, champion=active[0]['id'],
                                 scope="64-team main bracket; preliminary games excluded")
        all_games.extend(games)
    assert len(seasons) == 41 and len(all_games) == 2583
    manifest = dict(source=ARCHIVE_URL, commit=ARCHIVE_COMMIT, license="Unlicense",
                    files_sha256=hashes, seasons=sorted(map(int, seasons)),
                    bracket_advancements=len(all_games), played_games=sum(g['status']=='played' for g in all_games),
                    no_contests=1, missing_years=list(range(1939, 1985)), cancelled_years=[2020],
                    missing_fields=["scores", "game dates", "venues", "preliminary-round games", "preliminary-round losers"],
                    retrieval_date="2026-10-03")
    if persist:
        dump(ROOT / "data/derived/archive.json", seasons)
        dump(ROOT / "data/derived/provenance.json", manifest)
    return seasons, all_games


def games():
    return [g for s in read(ROOT / "data/derived/archive.json").values() for g in s['games'] if g['status']=='played']


def feature_table():
    path = ROOT / "data/derived/team_features.json"
    return read(path) if path.exists() else {}
