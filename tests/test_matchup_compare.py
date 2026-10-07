"""Verify comparison values and temporal/missing-data boundaries against real artifacts."""
import copy
import json
import subprocess
import pytest
from madness.server import load_state
from madness.model import predict
from madness.data import ROOT


@pytest.fixture(scope='module')
def state():
    return load_state()


def payload(state,year,game=None):
    year=str(year);archive=state['archive'][year]
    season=dict(archive,features=state['features'].get(year,{}),available_models=list(state['historical'].get(year,{})))
    game=game or archive['games'][-1]
    forecasts={}
    for kind,model in state['historical'].get(year,{}).items():
        if game['status']!='played':
            continue
        fa=season['features'].get(game['a']);fb=season['features'].get(game['b'])
        if kind=='form' and (not fa or not fb):
            continue
        p=predict(model,game['seed_a'],game['seed_b'],fa,fb)
        forecasts[kind]=dict(p_a=p,p_b=1-p,model=model)
    return dict(season=season,game=game,forecasts=forecasts)


def rows(data,swapped=False):
    code="""import {pathToFileURL} from 'node:url'; import fs from 'node:fs';
    const {comparisonRows}=await import(pathToFileURL(process.argv[1]).href);
    const x=JSON.parse(fs.readFileSync(0,'utf8'));
    try{process.stdout.write(JSON.stringify({rows:comparisonRows(x.season,x.game,x.forecasts,x.swapped)}));}
    catch(error){process.stdout.write(JSON.stringify({error:error.message}));}"""
    result=subprocess.run(['node','--input-type=module','-e',code,str(ROOT/'web/matchup_compare.js')],input=json.dumps(dict(data,swapped=swapped)),text=True,capture_output=True,check=True)
    return json.loads(result.stdout)


@pytest.mark.parametrize('year',[1985,1995,2006,2021,2026])
def test_comparison_is_same_game_prior_snapshot_and_symmetric(state,year):
    data=payload(state,year)
    original=rows(data)['rows'];swapped=rows(data,True)['rows']
    assert [row['kind'] for row in original]==['seed','seed_curve','form']
    for normal,reverse in zip(original,swapped):
        forecast=data['forecasts'].get(normal['kind'])
        if forecast:
            assert normal['p_a']==forecast['p_a'] and normal['p_b']==forecast['p_b']
            assert reverse['p_a']==normal['p_b'] and reverse['p_b']==normal['p_a']
            assert normal['through']<year
            assert normal['n_train']==forecast['model']['n_train']
            if normal['kind']!='seed':
                assert normal['gap']==pytest.approx((forecast['p_a']-data['forecasts']['seed']['p_a'])*100)
                assert reverse['gap']==pytest.approx(-normal['gap'])
        else:
            assert normal['missing'] and normal['p_a'] is None and normal['p_b'] is None
            assert normal['gap'] is None and normal['through'] is None and normal['n_train'] is None


def test_form_coverage_does_not_imply_a_model_and_no_contest_is_unscored(state):
    form=rows(payload(state,2006))['rows'][-1]
    assert 'Form features exist' in form['missing']
    assert form['p_a'] is None
    game=next(g for g in state['archive']['2021']['games'] if g['status']=='no_contest')
    actual=rows(payload(state,2021,game))['rows']
    assert all(row['p_a'] is None and row['p_b'] is None and 'No contest' in row['missing'] for row in actual)


@pytest.mark.parametrize('failure',['future','range','complement','missing'])
def test_invalid_or_missing_forecasts_never_render_as_valid(state,failure):
    data=copy.deepcopy(payload(state,2026))
    if failure=='future':
        data['forecasts']['seed']['model']['train_seasons'].append(2026)
    elif failure=='range':
        data['forecasts']['seed']['p_a']=1.5
    elif failure=='complement':
        data['forecasts']['seed']['p_b']=data['forecasts']['seed']['p_a']
    else:
        del data['forecasts']['seed']
    assert 'error' in rows(data)
