"""Local, dependency-light API and web server. No external service or authentication."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json
from .data import ROOT, read, feature_table
from .model import predict, vector
from .bracket import historical_field, simulate


def load_state():
    return dict(archive=read(ROOT/'data/derived/archive.json'), models=read(ROOT/'artifacts/models.json'),
                historical=read(ROOT/'artifacts/historical_models.json'), evaluation=read(ROOT/'artifacts/evaluation.json'),
                provenance=read(ROOT/'data/derived/provenance.json'), features=feature_table(),
                field=read(ROOT/'data/field_2027.json'),
                coverage=read(ROOT/'data/derived/schedule_coverage.json') if (ROOT/'data/derived/schedule_coverage.json').exists() else None)


def serve(port=8027):
    state = load_state()
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,directory=str(ROOT/'web'),**kwargs)

        def send_json(self,data,status=200):
            blob = json.dumps(data,allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(blob)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(blob)

        def resolve(self,year,kind):
            models = state['models']['models'] if year==2027 else state['historical'].get(str(year),{})
            if kind not in models:
                raise ValueError('This model has no historical training snapshot for the selected year.')
            return models[kind]

        def do_GET(self):
            parsed = urlparse(self.path)
            q = parse_qs(parsed.query)
            try:
                if parsed.path=='/api/summary':
                    return self.send_json(dict(provenance=state['provenance'],field=state['field'],
                                               evaluation=state['evaluation'],models=state['models'],
                                               coverage=state['coverage'],
                                               years=sorted(map(int,state['archive']),reverse=True)))
                if parsed.path=='/api/season':
                    year=int(q.get('year',['2026'])[0])
                    if str(year) not in state['archive']:
                        raise ValueError('No archive for that year; 2020 cancelled, 1939–1984 missing.')
                    season=state['archive'][str(year)]
                    model=state['historical'].get(str(year),{}).get('seed')
                    games=[]
                    for g in season['games']:
                        games.append(dict(g,p_a=predict(model,g['seed_a'],g['seed_b']) if model and g['status']=='played' else None))
                    return self.send_json(dict(season,games=games,features=state['features'].get(str(year),{}),
                                               available_models=list(state['historical'].get(str(year),{})),
                                               model=model,model_note='Retrospective pre-tournament seed model fitted only on earlier years.'))
                if parsed.path=='/api/predict':
                    year=int(q.get('year',['2027'])[0]); kind=q.get('model',['seed'])[0]
                    a=int(q.get('a',['1'])[0]); b=int(q.get('b',['16'])[0])
                    model=self.resolve(year,kind)
                    f=state['features'].get(str(year),{})
                    fa=f.get(q.get('team_a',[''])[0]); fb=f.get(q.get('team_b',[''])[0])
                    x=vector(a,b,kind,fa,fb)
                    p=predict(model,a,b,fa,fb)
                    return self.send_json(dict(p_a=p,p_b=1-p,model=model,
                                               contributions=[dict(feature=n,log_odds=v*c/model['temperature']) for n,v,c in zip(model['features'],x,model['coef'])]))
                if parsed.path=='/api/simulate':
                    year=int(q.get('year',['2026'])[0]); kind=q.get('model',['seed'])[0]
                    field=state['field'] if year==2027 else historical_field(state['archive'][str(year)])
                    return self.send_json(simulate(field,self.resolve(year,kind),state['features'].get(str(year),{}),int(q.get('rng',['2027'])[0])))
                if parsed.path.startswith('/api/'):
                    return self.send_json(dict(error='Unknown API route'),404)
                if parsed.path=='/':
                    self.path='/index.html'
                super().do_GET()
            except (ValueError,KeyError,TypeError) as e:
                self.send_json(dict(error=str(e)),400)

        def do_POST(self):
            try:
                if urlparse(self.path).path!='/api/simulate':
                    return self.send_json(dict(error='Unknown API route'),404)
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=100000:
                    raise ValueError('Import must be JSON under 100 KB.')
                payload=json.loads(self.rfile.read(length))
                field=payload['field']
                # Custom fields always use the current model and are explicitly prospective scenarios.
                return self.send_json(simulate(field,state['models']['models']['seed'],random_seed=int(payload.get('rng',2027))))
            except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:
                self.send_json(dict(error=str(e)),400)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'March Lab: http://127.0.0.1:{port}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
