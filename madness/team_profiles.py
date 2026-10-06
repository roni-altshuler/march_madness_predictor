"""Display-only tournament history from bundled labels and per-season crosswalks.

Verified schedule IDs join modern appearances. Uncrosswalked archive keys stay
in a separate namespace; spelling similarity never establishes school identity.
"""
from collections import defaultdict


def build_team_profiles(archive, features, provenance):
    profiles, assignments = {}, {}
    cancelled = set(provenance.get('cancelled_years', []))
    for year, season in sorted(archive.items(), key=lambda item: int(item[0])):
        season_year = int(year)
        if season_year in cancelled:
            raise ValueError('A cancelled tournament cannot have recorded appearances.')
        assignments[year] = {}
        seen = set()
        for team in season['teams']:
            raw_id = team['id']
            if raw_id in assignments[year]:
                raise ValueError('Duplicate archive team ID within a tournament.')
            feature = features.get(year, {}).get(raw_id, {})
            espn_id = feature.get('espn_id')
            key = f'espn:{espn_id}' if espn_id else f'archive:{raw_id}'
            if key in seen:
                raise ValueError('Two tournament teams share the same verified identity.')
            seen.add(key)
            assignments[year][raw_id] = key
            profile = profiles.setdefault(key, dict(
                id=key, identity_kind='verified_schedule_id' if espn_id else 'archive_key',
                source_id=str(espn_id) if espn_id else raw_id, appearances=[]))
            profile['name'] = team['name']
            games = []
            for game in sorted(season['games'], key=lambda g: g['round']):
                if raw_id not in (game['a'], game['b']):
                    continue
                is_a = game['a'] == raw_id
                opponent = game['b'] if is_a else game['a']
                won = game['winner'] == raw_id
                status = game['status']
                if status not in ('played', 'no_contest'):
                    raise ValueError('Unknown archived game status.')
                games.append(dict(
                    id=game['id'], round=game['round'], round_name=game['round_name'],
                    opponent_id=opponent,
                    opponent_name=next(t['name'] for t in season['teams'] if t['id']==opponent),
                    status=status, advanced=won,
                    result=('Won' if won else 'Lost') if status=='played' else
                           ('No contest · advanced' if won else 'No contest · did not advance'),
                    score_for=game.get('score_a' if is_a else 'score_b'),
                    score_against=game.get('score_b' if is_a else 'score_a'),
                    date_utc=game.get('date_utc')))
            if not games:
                raise ValueError('An archived appearance must have a recorded matchup.')
            played = [g for g in games if g['status']=='played']
            champion = season['champion'] == raw_id
            profile['appearances'].append(dict(
                year=season_year, archive_id=raw_id, name=team['name'], seed=team['seed'],
                region=team['slot']//16, champion=champion,
                final_stage='Champion' if champion else games[-1]['round_name'],
                played_wins=sum(g['advanced'] for g in played),
                played_losses=sum(not g['advanced'] for g in played),
                no_contests=sum(g['status']=='no_contest' for g in games),
                no_contest_advancements=sum(g['status']=='no_contest' and g['advanced'] for g in games),
                scores_and_dates=sum(g['score_for'] is not None and g['score_against'] is not None
                                     and bool(g['date_utc']) for g in played),
                form_available=bool(feature), games=games))

    overlaps = defaultdict(set)
    for profile in profiles.values():
        for appearance in profile['appearances']:
            overlaps[appearance['archive_id']].add(profile['id'])
            for game in appearance['games']:
                game['opponent_profile_id'] = assignments[str(appearance['year'])][game['opponent_id']]
        appearances = profile['appearances']
        profile['totals'] = dict(
            appearances=len(appearances), played_wins=sum(a['played_wins'] for a in appearances),
            played_losses=sum(a['played_losses'] for a in appearances),
            titles=sum(a['champion'] for a in appearances),
            no_contests=sum(a['no_contests'] for a in appearances),
            no_contest_advancements=sum(a['no_contest_advancements'] for a in appearances))
        profile['coverage'] = dict(
            archive_years=sorted(map(int, archive)), cancelled_years=sorted(cancelled),
            missing_years=provenance.get('missing_years', []),
            scope='Recorded main-bracket appearances only; preliminary games and losers are excluded.',
            identity_note=('Only appearances with this stored per-season ESPN ID are joined. '
                           'Earlier records without a verified crosswalk are kept separate.'
                           if profile['identity_kind']=='verified_schedule_id' else
                           'Exact archive-key records only. These have no verified school crosswalk '
                           'and are not combined with modern school identities.'),
            source=provenance['source'])
        appearances.sort(key=lambda a: a['year'], reverse=True)
    for profile in profiles.values():
        keys=set().union(*(overlaps[a['archive_id']] for a in profile['appearances']))-{profile['id']}
        profile['separate_records']=[dict(
            id=key, name=profiles[key]['name'], identity_kind=profiles[key]['identity_kind'],
            first_year=min(a['year'] for a in profiles[key]['appearances']),
            last_year=max(a['year'] for a in profiles[key]['appearances'])) for key in sorted(keys)]
    return dict(profiles=profiles, assignments=assignments)


def profile_teams(state, year):
    """Attach profile navigation IDs without changing source data or model inputs."""
    return [dict(team, profile_id=state['team_profiles']['assignments'][str(year)][team['id']])
            for team in state['archive'][str(year)]['teams']]
