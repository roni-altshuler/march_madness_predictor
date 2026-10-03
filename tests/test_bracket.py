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
