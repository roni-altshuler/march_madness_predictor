import argparse
from .data import ROOT, ingest_archive, read, dump
from .train import train
from .server import serve
from .bracket import historical_field, simulate

p=argparse.ArgumentParser(description='March Lab: archive, train, predict and simulate men\'s NCAA brackets.')
sub=p.add_subparsers(dest='command',required=True)
sub.add_parser('ingest',help='Reconstruct the bundled open historical archive.')
sub.add_parser('train',help='Fit and chronologically evaluate models.')
sub.add_parser('export',help='Build the static browser app from Python-computed probability tables.')
pr=sub.add_parser('predict',help='Reproducible prospective seed matchup inference.')
pr.add_argument('--a',type=int,required=True);pr.add_argument('--b',type=int,required=True)
pr.add_argument('--model',choices=['seed','seed_curve'],default='seed')
s=sub.add_parser('schedules',help='Download bounded optional open regular-season schedules.')
s.add_argument('--start',type=int,default=2006); s.add_argument('--end',type=int,default=2026)
s.add_argument('--refresh-source',action='store_true',help='Explicitly accept changed source checksums and regenerate coverage.')
web=sub.add_parser('serve'); web.add_argument('--port',type=int,default=8027)
sim=sub.add_parser('simulate'); sim.add_argument('--year',type=int,default=2026)
sim.add_argument('--field'); sim.add_argument('--output',default='artifacts/simulation.json'); sim.add_argument('--rng',type=int,default=2027)
args=p.parse_args()
if args.command=='ingest':
    seasons,g=ingest_archive(); print(f'{len(seasons)} tournaments, {len(g)} advancements')
elif args.command=='schedules':
    from .schedules import download_schedules, build_features
    if not 2003<=args.start<=args.end<=2026:
        p.error('Use a bounded historical range within 2003–2026.')
    download_schedules([y for y in range(args.start,args.end+1) if y!=2020],args.refresh_source)
    print([(r['season'],r['mapped_main_bracket_teams']) for r in build_features()])
elif args.command=='train':
    report=train()
    print({k:None if m is None else {n:round(m[n],5) for n in ('n','brier','log_loss','ece')} for k,m in report['holdout_metrics'].items()})
elif args.command=='predict':
    from .model import predict
    import json
    m=read(ROOT/'artifacts/models.json')['models'][args.model]
    probability=predict(m,args.a,args.b)
    print(json.dumps(dict(seed_a=args.a,seed_b=args.b,p_a=probability,p_b=1-probability,model=args.model,train_through=max(m['train_seasons']))))
elif args.command=='export':
    from .export import export_static
    export_static()
elif args.command=='serve':
    serve(args.port)
elif args.command=='simulate':
    field=read(args.field) if args.field else historical_field(read(ROOT/'data/derived/archive.json')[str(args.year)])
    model=read(ROOT/'artifacts/models.json')['models']['seed'] if args.field else read(ROOT/'artifacts/historical_models.json')[str(args.year)]['seed']
    result=simulate(field,model,random_seed=args.rng); dump(args.output,result)
    print(f"{result['participants']} teams, {result['total_games']} games; wrote {args.output}")
