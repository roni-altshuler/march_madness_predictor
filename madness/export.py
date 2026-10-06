"""Public static build: publish Python-computed lookup tables, never train in a browser."""
import shutil
import hashlib
from .data import ROOT,dump
from .server import load_state
from .model import predict,vector
from .team_profiles import profile_teams


def export_static():
    state=load_state();output=ROOT/'public';output.mkdir(exist_ok=True)
    for source in (ROOT/'web').glob('*'):
        if source.is_file():
            shutil.copyfile(source,output/source.name)
    index=(output/'index.html').read_text(encoding='utf-8')
    index=index.replace('<head>','<head>\n<meta name="march-mode" content="static">')
    index=index.replace('href="/style.css"','href="./style.css"').replace('src="/app.js"','src="./app.js"')
    (output/'index.html').write_text(index,encoding='utf-8',newline='\n')
    (output/'.nojekyll').write_text('',encoding='utf-8')
    summary={k:state[k] for k in ('provenance','field','evaluation','models','coverage')}
    summary['years']=sorted(map(int,state['archive']),reverse=True)
    dump(output/'data/summary.json',summary)
    team_index = {}
    for key, profile in state['team_profiles']['profiles'].items():
        filename = hashlib.sha256(key.encode('utf-8')).hexdigest()+'.json'
        team_index[key] = dict(file=filename)
        dump(output/'data/teams'/filename,profile)
    dump(output/'data/teams/index.json',dict(profiles=team_index))
    for year,season in state['archive'].items():
        models=state['historical'].get(year,{})
        m=models.get('seed')
        sg=[dict(g,p_a=predict(m,g['seed_a'],g['seed_b']) if m and g['status']=='played' else None) for g in season['games']]
        dump(output/f'data/seasons/{year}.json',dict(season,teams=profile_teams(state,year),games=sg,features=state['features'].get(year,{}),
             available_models=list(models),model=m,model_note='Retrospective model fitted only on earlier tournaments.'))
    for year in [*state['historical'],'2027']:
        models=state['models']['models'] if year=='2027' else state['historical'][year]
        table=dict(season=int(year),models=models,teams=list(state['features'].get(year,{})),seed={},form=None)
        for kind in ('seed','seed_curve'):
            if kind not in models:continue
            m=models[kind]
            table['seed'][kind]=dict(
                probabilities=[[predict(m,a,b) for b in range(1,17)] for a in range(1,17)],
                contributions=[[[float(v*c/m['temperature']) for v,c in zip(vector(a,b,kind),m['coef'])] for b in range(1,17)] for a in range(1,17)])
        if 'form' in models and year!='2027':
            f=state['features'][year];seeds={t['id']:t['seed'] for t in state['archive'][year]['teams']}
            table['form']=[[predict(models['form'],seeds[a],seeds[b],f[a],f[b]) for b in table['teams']] for a in table['teams']]
        dump(output/f'data/tables/{year}.json',table)
    print(f'Static app exported to {output}',flush=True)
    return output
