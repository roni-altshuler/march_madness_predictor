import copy
import math
import pytest
from madness.bracket import historical_field,validate_field,simulate
from madness.data import ROOT,read


@pytest.fixture
def field():
    return historical_field(read(ROOT/'data/derived/archive.json')['2026'])


def test_exact_probability_mass_and_valid_draw(field):
    model=read(ROOT/'artifacts/historical_models.json')['2026']['seed']
    result=simulate(field,model,random_seed=42)
    assert result==simulate(field,model,random_seed=42)
    assert result['participants']==64 and result['total_games']==63
    for key,total in [('reach_round64',64),('reach_round32',32),('reach_sweet16',16),('reach_elite8',8),('reach_final4',4),('reach_final',2),('champion',1)]:
        assert math.isclose(sum(t[key] for t in result['odds']),total,abs_tol=1e-10)
    previous={t['id'] for s in field['slots'] for t in s}
    for r in result['sampled_rounds']:
        assert {g[k] for g in r['games'] for k in ('a','b')}==previous
        assert all(g['winner'] in (g['a'],g['b']) for g in r['games'])
        previous={g['winner'] for g in r['games']}


def test_76_team_format_and_opening_mass(field):
    # Structural test fixture only; these added IDs are never published as tournament data.
    f=copy.deepcopy(field);f.update(season=2027,expected_teams=76,expected_opening_games=12)
    for i in range(12):
        t=dict(f['slots'][i][0]);t['id']=f'test-only-{i}';t['name']=t['id'];f['slots'][i].append(t)
    model=dict(kind='seed',coef=[0],temperature=1)
    r=simulate(f,model)
    assert r['participants']==76 and r['opening_games']==12 and r['total_games']==75
    assert len(r['sampled_opening'])==12
    assert math.isclose(sum(t['champion'] for t in r['odds']),1,abs_tol=1e-12)
    assert sum(t['reach_round64']==.5 for t in r['odds'])==24
    assert sum(t['reach_round64']==1 for t in r['odds'])==52


def test_unknown_2027_is_not_forecast():
    with pytest.raises(ValueError,match='unknown'):
        validate_field(read(ROOT/'data/field_2027.json'))


def test_wrong_2027_format_rejected(field):
    f=copy.deepcopy(field);f['season']=2027
    with pytest.raises(ValueError,match='76 teams'): validate_field(f)


def test_duplicate_teams_and_wrong_pairing_rejected(field):
    f=copy.deepcopy(field);f['slots'][1][0]['id']=f['slots'][0][0]['id']
    with pytest.raises(ValueError,match='unique'): validate_field(f)
    f=copy.deepcopy(field);f['slots'][0],f['slots'][1]=f['slots'][1],f['slots'][0]
    with pytest.raises(ValueError,match='bracket seed order'): validate_field(f)


@pytest.mark.parametrize('bad',[[],None,{'season':'<script>'},{'season':2027,'slots':None}])
def test_malformed_json_field_is_rejected(bad):
    with pytest.raises(ValueError): validate_field(bad)


def assert_recommended_path(field,result,model,features=None):
    from madness.model import predict
    teams={t['id']:t for s in field['slots'] for t in s};features=features or {}
    rec=result['recommended'];opening=iter(rec['opening']);previous=[]
    for slot in field['slots']:
        if len(slot)==1:previous.append(slot[0]['id']);continue
        game=next(opening);assert [game['a'],game['b']]==[t['id'] for t in slot]
        previous.append(game['winner'])
    assert next(opening,None) is None
    count=len(rec['opening'])
    for round_ in rec['rounds']:
        assert [team for g in round_['games'] for team in [g['a'],g['b']]]==previous
        count+=len(round_['games']);previous=[g['winner'] for g in round_['games']]
    assert previous==[rec['champion']] and count==len(teams)-1
    for g in rec['opening']+[g for r in rec['rounds'] for g in r['games']]:
        p=predict(model,teams[g['a']]['seed'],teams[g['b']]['seed'],features.get(g['a']),features.get(g['b']))
        assert g['p_a']==p
        assert g['winner']==(g['a'] if p>=.5 else g['b'])
    assert rec['champion_probability']==next(t['champion'] for t in result['odds'] if t['team']==rec['champion'])


@pytest.mark.parametrize('year',[1995,2015,2026])
def test_recommendation_is_complete_deterministic_and_prior_only(year):
    f=historical_field(read(ROOT/'data/derived/archive.json')[str(year)])
    model=read(ROOT/'artifacts/historical_models.json')[str(year)]['seed']
    first=simulate(f,model,random_seed=42);second=simulate(f,model,random_seed=73)
    assert first['recommended']==second['recommended']
    assert first['sampled_rounds']!=second['sampled_rounds']
    assert first['recommended']['trained_through']<year
    assert first['recommended']['calibration_through'] is None or first['recommended']['calibration_through']<year
    assert first['recommended']['form_cutoff_utc'] is None
    assert_recommended_path(f,first,model)


def test_recommendation_ignores_observed_results(field):
    archive=read(ROOT/'data/derived/archive.json')['2026'];changed=copy.deepcopy(archive)
    changed['games']=[];changed['champion']='TEST-ONLY-DISCARDED-RESULT'
    for team in changed['teams']:team['wins']=99
    assert historical_field(changed)==field
    model=read(ROOT/'artifacts/historical_models.json')['2026']['seed']
    assert simulate(historical_field(changed),model)['recommended']==simulate(field,model)['recommended']


def test_first_four_dependencies_and_exact_ties(field):
    # Four opening pairs are structural fixtures, never published as actual entrants.
    f=copy.deepcopy(field);f.update(expected_teams=68,expected_opening_games=4)
    for i in [1,5,17,21]:
        t=dict(f['slots'][i][0]);t.update(id=f'test-only-opening-{i}',name=f'Test only opening {i}')
        f['slots'][i].append(t)
    model=dict(kind='seed',coef=[0],temperature=1)
    result=simulate(f,model,random_seed=42);assert_recommended_path(f,result,model)
    rec=result['recommended'];assert len(rec['opening'])==4
    assert all(g['p_a']==.5 and g['winner']==g['a'] for g in rec['opening'])
    assert not any(g['a'].startswith('test-only') or g['b'].startswith('test-only') for r in rec['rounds'] for g in r['games'])
    assert rec['champion']==f['slots'][0][0]['id']
    assert rec['trained_through'] is None  # Fixture does not invent a trained snapshot.
