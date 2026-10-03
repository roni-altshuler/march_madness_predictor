import math
import hashlib
import numpy as np
import pytest
from madness.data import ROOT, read, games, ingest_archive, feature_table
from madness.model import fit, predict, vector, metrics, calibrate


def test_archive_graph_and_no_contest():
    archive,all_games=ingest_archive(persist=False)
    assert len(archive)==41 and '2020' not in archive
    assert len(all_games)==2583 and len(games())==2582
    for season in archive.values():
        assert [sum(g['round']==r for g in season['games']) for r in range(1,7)]==[32,16,8,4,2,1]
        for r in range(1,6):
            winners={g['winner'] for g in season['games'] if g['round']==r}
            participants={g[t] for g in season['games'] if g['round']==r+1 for t in ('a','b')}
            assert winners==participants
    nc=[g for g in all_games if g['status']=='no_contest']
    assert len(nc)==1 and {nc[0]['a'],nc[0]['b']}=={'Oregon','VACommonwealth'}
    assert archive['1985']['champion']=='Villanova'
    assert archive['2025']['champion']=='Florida'
    assert archive['2026']['champion']=='Michigan'
    manifest=read(ROOT/'data/derived/provenance.json')
    for name,expected in manifest['files_sha256'].items():
        assert hashlib.sha256((ROOT/'data/archive'/name).read_bytes()).hexdigest()==expected


def test_seed_probability_symmetry_and_order():
    model=read(ROOT/'artifacts/models.json')['models']['seed']
    for a in range(1,17):
        for b in range(1,17):
            p=predict(model,a,b)
            assert 0<p<1 and math.isclose(p+predict(model,b,a),1,abs_tol=1e-14)
            assert p==.5 if a==b else p>.5 if a<b else p<.5


@pytest.mark.parametrize('seed',[0,17,1.5,True,'5'])
def test_invalid_seeds(seed):
    with pytest.raises(ValueError): vector(seed,1)


def test_temporal_training_and_calibration():
    snapshots=read(ROOT/'artifacts/historical_models.json')
    for year,models in snapshots.items():
        for model in models.values():
            assert max(model['train_seasons'])<int(year)
            assert model.get('calibration_through',0)<int(year)
    predictions=read(ROOT/'artifacts/predictions.json')
    for kind in ('seed','seed_curve','form'):
        for row in predictions[kind]:
            assert row['train_through']<row['season']
            assert row['calibration_through'] is None or row['calibration_through']<row['season']


def test_future_outcomes_do_not_change_earlier_fit():
    rows=games();features=feature_table()
    before=[g for g in rows if g['season']<2019]
    original=fit(before,'seed',features)
    changed=[dict(g,winner=g['b'] if g['winner']==g['a'] else g['a']) if g['season']>=2019 else g for g in rows]
    replay=fit([g for g in changed if g['season']<2019],'seed',features)
    assert original==replay
    assert all(len(vector(g['seed_a'],g['seed_b']))==1 for g in before)


def test_report_recomputed_from_predictions():
    r=read(ROOT/'artifacts/evaluation.json');predictions=read(ROOT/'artifacts/predictions.json')
    for kind,rows in predictions.items():
        selected=[x for x in rows if 2021<=x['season']<=2026]
        actual=metrics(selected);expected=r['holdout_metrics'][kind]
        for key in ('n','brier','log_loss','accuracy','ece'):
            assert actual[key]==pytest.approx(expected[key],abs=1e-12)
    assert r['holdout_metrics']['seed']['n']==377


def test_feature_horizon_and_coverage():
    features=feature_table()
    for year,teams in features.items():
        for f in teams.values():
            assert f['cutoff_utc']==f'{year}-03-01T00:00:00+00:00'
            assert f['games']>=10 and 0<=f['win_rate']<=1
            assert math.isfinite(f['elo']) and math.isfinite(f['margin'])
    assert len(features['2026'])==64
    assert features['2023']['Lafayette']['source_name']=='Louisiana'
    assert features['2025']['SanDiego']['source_name']=='UC San Diego'


def test_modern_scores_cross_validate_all_played_results():
    archive=read(ROOT/'data/derived/archive.json')
    modern=[g for year,s in archive.items() if int(year)>=2006 for g in s['games'] if g['status']=='played']
    assert len(modern)==1259
    assert all(g['score_a'] is not None and g['date_utc'] for g in modern)
    assert all((g['a'] if g['score_a']>g['score_b'] else g['b'])==g['winner'] for g in modern)


def test_calibration_requires_prior_history():
    m=dict(kind='seed',coef=[3],train_seasons=[1985],temperature=1)
    assert calibrate(m,[])['temperature']==1
