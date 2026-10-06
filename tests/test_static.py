import copy
import json
import subprocess
import pytest
from madness.data import ROOT,read,feature_table
from madness.bracket import historical_field,simulate
from madness.export import export_static
from madness.model import predict
from madness.server import load_state
import hashlib


@pytest.fixture(scope='module')
def public():
    return export_static()


def browser_simulation(field,table,kind='seed'):
    source=ROOT/'web/static_api.js'
    code="import {pathToFileURL} from 'node:url'; import fs from 'node:fs'; const {simulate}=await import(pathToFileURL(process.argv[1]).href); const x=JSON.parse(fs.readFileSync(0,'utf8')); process.stdout.write(JSON.stringify(simulate(x.field,x.table,x.kind,42)));"
    r=subprocess.run(['node','--input-type=module','-e',code,str(source)],input=json.dumps(dict(field=field,table=table,kind=kind)),text=True,capture_output=True,check=True)
    return json.loads(r.stdout)


def test_published_seed_and_form_tables_match_python(public):
    table=read(public/'data/tables/2026.json');f=feature_table()['2026']
    for kind in ('seed','seed_curve'):
        for a in range(1,17):
            for b in range(1,17):
                assert table['seed'][kind]['probabilities'][a-1][b-1]==predict(table['models'][kind],a,b)
    teams=read(public/'data/seasons/2026.json')['teams'];seeds={t['id']:t['seed'] for t in teams}
    for a in ('Duke','Connecticut','Michigan'):
        for b in ('Duke','Connecticut','Michigan'):
            i,j=table['teams'].index(a),table['teams'].index(b)
            assert table['form'][i][j]==predict(table['models']['form'],seeds[a],seeds[b],f[a],f[b])


@pytest.mark.parametrize('kind',['seed','seed_curve','form'])
def test_static_bracket_matches_python(public,kind):
    field=historical_field(read(ROOT/'data/derived/archive.json')['2026'])
    table=read(public/'data/tables/2026.json')
    python=simulate(field,table['models'][kind],feature_table()['2026'],42)
    browser=browser_simulation(field,table,kind)
    assert browser['sampled_rounds']==python['sampled_rounds']
    for expected,actual in zip(python['odds'],browser['odds']):
        assert expected['team']==actual['team']
        for key in ('reach_round64','reach_round32','reach_sweet16','reach_elite8','reach_final4','reach_final','champion'):
            assert expected[key]==pytest.approx(actual[key],abs=1e-12)


def test_static_76_team_draw_matches_python(public):
    field=historical_field(read(ROOT/'data/derived/archive.json')['2026'])
    field.update(season=2027,expected_teams=76,expected_opening_games=12)
    for i in range(12):
        t=dict(field['slots'][i][0]);t.update(id=f'test-only-{i}',name=f'Test only {i}');field['slots'][i].append(t)
    table=read(public/'data/tables/2027.json')
    python=simulate(field,table['models']['seed'],random_seed=42)
    browser=browser_simulation(field,table)
    assert browser['sampled_opening']==python['sampled_opening']
    assert browser['sampled_rounds']==python['sampled_rounds']
    assert sum(t['champion'] for t in browser['odds'])==pytest.approx(1,abs=1e-12)


def test_static_profiles_match_api_state_with_safe_exact_paths(public):
    state=load_state();index=read(public/'data/teams/index.json')['profiles']
    assert set(index)==set(state['team_profiles']['profiles'])
    for key,entry in index.items():
        assert entry['file']==hashlib.sha256(key.encode()).hexdigest()+'.json'
        assert read(public/'data/teams'/entry['file'])==state['team_profiles']['profiles'][key]
    for year in ('1985','2008','2025','2026'):
        teams=read(public/f'data/seasons/{year}.json')['teams']
        assert all(t['profile_id']==state['team_profiles']['assignments'][year][t['id']] for t in teams)


def test_static_profile_lookup_rejects_missing_and_inherited_keys(public):
    code="""import {pathToFileURL} from 'node:url'; import fs from 'node:fs';
    const root=process.argv[2],fetched=[];
    globalThis.fetch=async url=>{const path=new URL(url).pathname.split('/data/')[1];fetched.push(path);return {ok:true,json:async()=>JSON.parse(fs.readFileSync(root+'/data/'+path,'utf8'))};};
    const {request}=await import(pathToFileURL(process.argv[1]).href);
    for(const id of ['missing','__proto__','constructor','../../summary']){
      try{await request('/api/team?profile='+encodeURIComponent(id));throw Error('unexpected profile');}
      catch(e){if(!e.message.includes('exact profile ID'))throw e;}
    }
    const profile=await request('/api/team?profile=espn%3A150');
    process.stdout.write(JSON.stringify({id:profile.id,fetched}));"""
    result=subprocess.run(['node','--input-type=module','-e',code,str(ROOT/'web/static_api.js'),str(public)],text=True,capture_output=True,check=True)
    actual=json.loads(result.stdout)
    assert actual['id']=='espn:150'
    assert actual['fetched']==['teams/index.json','teams/'+hashlib.sha256(b'espn:150').hexdigest()+'.json']
