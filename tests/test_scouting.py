"""Scouting calculations use frozen field features and strictly earlier snapshots."""
import copy
import json
import subprocess
import pytest
from madness.data import ROOT
from madness.server import load_state
from madness.model import predict
from madness.scouting import add_scouting_context, field_form_context


@pytest.fixture(scope='module')
def state():
    return load_state()


def browser_summary(profile, year, window='5'):
    code="""import {pathToFileURL} from 'node:url'; import fs from 'node:fs';
    const {scoutingSummary}=await import(pathToFileURL(process.argv[1]).href);
    const x=JSON.parse(fs.readFileSync(0,'utf8'));
    try{process.stdout.write(JSON.stringify(scoutingSummary(x.profile,x.year,x.window)));}
    catch(error){process.stdout.write(JSON.stringify({error:error.message}));}"""
    result=subprocess.run(['node','--input-type=module','-e',code,str(ROOT/'web/team_scouting.js')],
                          input=json.dumps(dict(profile=profile,year=year,window=window)),
                          text=True,capture_output=True,check=True)
    return json.loads(result.stdout)


@pytest.mark.parametrize('identity,year,window',[
    ('espn:150',2026,'5'),('espn:150',2015,'3'),('espn:150',2006,'all'),
    ('archive:Duke',2005,'all'),('archive:Duke',1990,'5'),('espn:2670',2025,'all')])
def test_earlier_signal_matches_saved_models_on_identical_played_games(state,identity,year,window):
    profile=state['team_profiles']['profiles'][identity]
    actual=browser_summary(profile,year,window)
    records=sorted([r for r in profile['appearances'] if r['year']<year],key=lambda r:r['year'],reverse=True)
    if window!='all': records=records[:int(window)]
    assert [r['year'] for r in actual['records']]==[r['year'] for r in records]
    expected=wins=covered=0
    for record in records:
        model=state['historical'].get(str(record['year']),{}).get('seed')
        for game in state['archive'][str(record['year'])]['games']:
            if record['archive_id'] not in (game['a'],game['b']) or game['status']!='played' or not model:
                continue
            p=predict(model,game['seed_a'],game['seed_b'])
            expected+=p if game['a']==record['archive_id'] else 1-p
            wins+=game['winner']==record['archive_id'];covered+=1
    assert actual['scoredGames']==covered
    assert actual['recordedWins']==(wins if covered else None)
    assert actual['expectedWins']==pytest.approx(expected) if covered else actual['expectedWins'] is None
    assert actual['difference']==pytest.approx(wins-expected) if covered else actual['difference'] is None
    assert actual['playedGames']==sum(r['played_wins']+r['played_losses'] for r in records)
    assert actual['noContests']==sum(r['no_contests'] for r in records)


def test_selected_and_future_outcomes_cannot_change_earlier_signal(state):
    profile=copy.deepcopy(state['team_profiles']['profiles']['espn:150'])
    before=browser_summary(profile,2015,'all')
    for record in profile['appearances']:
        if record['year']>=2015:
            record.update(played_wins=999,played_losses=999)
            for game in record['games']:
                game.update(advanced=not game['advanced'],seed_probability=999,seed_trained_through=2099)
    assert browser_summary(profile,2015,'all')==before


def test_uncrosswalked_and_no_contest_records_are_not_scored_or_joined(state):
    modern=state['team_profiles']['profiles']['espn:150']
    assert browser_summary(modern,2006,'all')['records']==[]
    old=browser_summary(state['team_profiles']['profiles']['archive:Duke'],1990,'all')
    assert old['playedGames']>0 and old['scoredGames']==0 and old['expectedWins'] is None
    record=next(r for r in state['team_profiles']['profiles']['espn:2670']['appearances'] if r['year']==2021)
    assert record['seed_expectation']==dict(scored_games=0,recorded_wins=None,expected_wins=None,difference=None)
    assert all(g['seed_probability'] is None and g['seed_trained_through'] is None for g in record['games'])


def test_field_percentiles_use_matching_cutoff_finite_values_and_ties(state):
    season=state['archive']['2026'];features=copy.deepcopy(state['features']['2026'])
    context=field_form_context(season,features,'Duke')
    for kind,metric in context['metrics'].items():
        values=[features[t['id']][kind] for t in season['teams']]
        value=features['Duke'][kind]
        assert metric['percentile']==pytest.approx(100*(sum(v<value for v in values)+.5*sum(v==value for v in values))/len(values))
        assert metric['covered_teams']==len(season['teams'])
    first,second,third=season['teams'][:3]
    for t in season['teams']: features[t['id']]['elo']=None
    features[first['id']]['elo']=features[second['id']]['elo']=1500
    features[third['id']]['elo']=float('nan')
    tied=field_form_context(season,features,first['id'])['metrics']['elo']
    assert tied==dict(value=1500,percentile=50,covered_teams=2)
    features[first['id']]['cutoff_utc']='2026-03-02T00:00:00+00:00'
    invalid=field_form_context(season,features,first['id'])
    assert invalid['cutoff_utc'] is None
    assert all(m['value'] is None and m['percentile'] is None for m in invalid['metrics'].values())
    assert invalid['metrics']['elo']['covered_teams']==1


def test_enrichment_preserves_source_and_baseline_artifacts(state):
    copied=copy.deepcopy(state)
    add_scouting_context(copied)
    for key in ('archive','features','historical','models','evaluation'):
        assert copied[key]==state[key]
    copied['historical']['2026']['seed']['train_seasons'].append(2026)
    with pytest.raises(ValueError,match='strictly before'):
        add_scouting_context(copied)


@pytest.mark.parametrize('failure',['future_horizon','range'])
def test_browser_rejects_invalid_earlier_probabilities(state,failure):
    profile=copy.deepcopy(state['team_profiles']['profiles']['espn:150'])
    game=next(r for r in profile['appearances'] if r['year']==2025)['games'][0]
    game.update({'seed_trained_through':2025} if failure=='future_horizon' else {'seed_probability':1.5})
    assert 'error' in browser_summary(profile,2026)
