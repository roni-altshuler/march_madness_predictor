"""Identity and aggregate checks against existing published tournament records."""
import copy
import pytest
from madness.server import load_state
from madness.team_profiles import build_team_profiles, profile_teams


@pytest.fixture(scope='module')
def state():
    return load_state()


def test_reused_archive_labels_do_not_join_different_schools(state):
    assignments = state['team_profiles']['assignments']
    assert assignments['2008']['SanDiego'] == 'espn:301'
    assert assignments['2025']['SanDiego'] == 'espn:28'
    assert assignments['2015']['Lafayette'] == 'espn:322'
    assert assignments['2023']['Lafayette'] == 'espn:309'
    profiles = state['team_profiles']['profiles']
    assert [a['year'] for a in profiles['espn:301']['appearances']] == [2008]
    assert [a['year'] for a in profiles['espn:28']['appearances']] == [2025]
    assert 'espn:28' in {p['id'] for p in profiles['espn:301']['separate_records']}
    assert assignments['2023']['MiamiFL'] != assignments['2026']['MiamiOH']


def test_uncrosswalked_records_are_scoped_and_source_inputs_unchanged(state):
    archive, features = copy.deepcopy(state['archive']), copy.deepcopy(state['features'])
    result = build_team_profiles(archive, features, state['provenance'])
    assert archive == state['archive'] and features == state['features']
    old, modern = result['profiles']['archive:Duke'], result['profiles']['espn:150']
    assert max(a['year'] for a in old['appearances']) == 2005
    assert min(a['year'] for a in modern['appearances']) == 2006
    assert old['totals']['appearances'] == 20 and modern['totals']['appearances'] == 19
    assert 'no verified school crosswalk' in old['coverage']['identity_note']
    assert 'espn:150' in {p['id'] for p in old['separate_records']}
    teams = profile_teams(state, 2026)
    assert teams[0]['profile_id'] == 'espn:150'
    assert 'profile_id' not in state['archive']['2026']['teams'][0]


def test_names_can_change_only_when_published_identity_agrees(state):
    # Rename an in-memory copy to exercise crosswalk joins; no fixture is published.
    archive = copy.deepcopy({y:state['archive'][y] for y in ('2025','2026')})
    features = copy.deepcopy({y:state['features'][y] for y in archive})
    team = next(t for t in archive['2025']['teams'] if t['id']=='Duke')
    team.update(id='test-only-renamed-key', name='Test-only recorded name')
    features['2025']['test-only-renamed-key'] = features['2025'].pop('Duke')
    for game in archive['2025']['games']:
        for key in ('a','b','winner'):
            if game[key]=='Duke':
                game[key]='test-only-renamed-key'
    result = build_team_profiles(archive, features, state['provenance'])
    assert {a['archive_id'] for a in result['profiles']['espn:150']['appearances']} == {'Duke','test-only-renamed-key'}
    features['2025']['test-only-renamed-key']['espn_id']='test-only-distinct'
    result = build_team_profiles(archive, features, state['provenance'])
    assert len(result['profiles']['espn:150']['appearances']) == 1


def test_duplicate_verified_id_within_tournament_is_rejected(state):
    archive = {'2026':state['archive']['2026']}
    features = copy.deepcopy({'2026':state['features']['2026']})
    teams = archive['2026']['teams']
    features['2026'][teams[1]['id']]['espn_id']=features['2026'][teams[0]['id']]['espn_id']
    with pytest.raises(ValueError, match='same verified identity'):
        build_team_profiles(archive, features, state['provenance'])


def test_no_contests_and_cancelled_missing_history_are_explicit(state):
    profiles = state['team_profiles']['profiles']
    oregon = next(a for a in profiles['espn:2483']['appearances'] if a['year']==2021)
    vcu = next(a for a in profiles['espn:2670']['appearances'] if a['year']==2021)
    assert (oregon['played_wins'],oregon['played_losses'],oregon['no_contest_advancements']) == (1,1,1)
    assert (vcu['played_wins'],vcu['played_losses'],vcu['no_contest_advancements']) == (0,0,0)
    assert vcu['games'][0]['result']=='No contest · did not advance'
    assert vcu['games'][0]['score_for'] is None
    assert all(a['year']!=2020 for p in profiles.values() for a in p['appearances'])
    assert 'espn:unknown' not in profiles and 'archive:missing' not in profiles
    assert profiles['espn:150']['coverage']['cancelled_years'] == [2020]
    with pytest.raises(ValueError, match='cancelled tournament'):
        build_team_profiles({'2020':state['archive']['2026']}, {}, state['provenance'])


def test_aggregates_recomputed_from_archive_and_exact_crosswalk(state):
    profiles = state['team_profiles']['profiles']
    assert sum(p['totals']['appearances'] for p in profiles.values()) == 41*64
    assert sum(p['totals']['played_wins'] for p in profiles.values()) == 2582
    assert sum(p['totals']['played_losses'] for p in profiles.values()) == 2582
    assert sum(p['totals']['titles'] for p in profiles.values()) == 41
    assert sum(p['totals']['no_contests'] for p in profiles.values()) == 2
    assert sum(p['totals']['no_contest_advancements'] for p in profiles.values()) == 1
    for profile in profiles.values():
        wins=losses=titles=0
        for record in profile['appearances']:
            year=str(record['year']);raw=record['archive_id'];season=state['archive'][year]
            espn=state['features'].get(year,{}).get(raw,{}).get('espn_id')
            assert profile['id']==(f'espn:{espn}' if espn else f'archive:{raw}')
            games=[g for g in season['games'] if raw in (g['a'],g['b']) and g['status']=='played']
            wins += sum(g['winner']==raw for g in games)
            losses += sum(g['winner']!=raw for g in games)
            titles += season['champion']==raw
        assert (wins,losses,titles)==tuple(profile['totals'][k] for k in ('played_wins','played_losses','titles'))
