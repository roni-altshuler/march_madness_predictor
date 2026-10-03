"""Expanding-window tournament evaluation; season is the unit of time separation."""
from .data import ROOT, dump, games, feature_table
from .model import fit, design, calibrate, predict, metrics
import numpy as np


def paired_uncertainty(records, challenger, baseline='seed'):
    """Tournament-cluster bootstrap: each sampled year keeps all of its games."""
    a={r['game_id']:r for r in records[challenger] if 2021<=r['season']<=2026}
    b={r['game_id']:r for r in records[baseline] if r['game_id'] in a}
    paired=[(a[i],b[i]) for i in sorted(a.keys() & b.keys())]
    years=sorted({x['season'] for x,_ in paired})
    if len(years)<2:
        return None
    sums=[];counts=[]
    for year in years:
        gaps=[(x['p']-x['y'])**2-(y['p']-y['y'])**2 for x,y in paired if x['season']==year]
        sums.append(sum(gaps));counts.append(len(gaps))
    rng=np.random.default_rng(2027)
    indices=rng.integers(0,len(years),size=(5000,len(years)))
    gaps=np.asarray(sums)[indices].sum(axis=1)/np.asarray(counts)[indices].sum(axis=1)
    return dict(challenger=challenger,baseline=baseline,n=len(paired),tournaments=len(years),
                brier_gap=sum(sums)/sum(counts),interval95=np.quantile(gaps,[.025,.975]).tolist(),
                note='5,000 paired tournament-cluster bootstrap samples; only six test tournaments, so interval estimates are unstable.')


def train():
    rows, features = games(), feature_table()
    years = sorted({g['season'] for g in rows})
    records = {k:[] for k in ('coin', 'seed_pick', 'seed', 'seed_curve', 'form')}
    snapshots = {}
    prior_raw = {k:[] for k in ('seed', 'seed_curve', 'form')}
    for year in years:
        if year < 1995:
            continue
        before = [g for g in rows if g['season'] < year]
        current = [g for g in rows if g['season'] == year]
        snapshots[str(year)] = {}
        for kind in ('seed', 'seed_curve', 'form'):
            try:
                model = calibrate(fit(before, kind, features), prior_raw[kind])
            except ValueError:
                continue
            assert max(model['train_seasons']) < year
            if model.get('calibration_n'):
                assert model['calibration_through'] < year
            snapshots[str(year)][kind] = model
            _, _, selected = design(current, kind, features)
            for g in selected:
                f = features.get(str(year), {})
                raw = predict(dict(model,temperature=1), g['seed_a'],g['seed_b'],f.get(g['a']),f.get(g['b']))
                p = predict(model,g['seed_a'],g['seed_b'],f.get(g['a']),f.get(g['b']))
                record = dict(game_id=g['id'], season=year, round=g['round'], y=int(g['winner']==g['a']), p=p,
                              train_through=max(model['train_seasons']), calibration_through=model.get('calibration_through'))
                records[kind].append(record)
                prior_raw[kind].append(dict(record,p=raw))
        for g in current:
            base = dict(game_id=g['id'],season=year,round=g['round'],y=int(g['winner']==g['a']))
            records['coin'].append(dict(base,p=.5))
            # A deterministic seed pick is not a meaningful log-loss forecaster. Use explicit 75% confidence.
            p = .75 if g['seed_a']<g['seed_b'] else .25 if g['seed_a']>g['seed_b'] else .5
            records['seed_pick'].append(dict(base,p=p))
    def summarize(start,end, ids=None):
        return {k:metrics([r for r in v if start<=r['season']<=end and (ids is None or r['game_id'] in ids)])
                for k,v in records.items()}
    form_ids = {r['game_id'] for r in records['form']}
    report = dict(protocol='Expanding-window annual refit; test labels never enter their own model or calibration.',
                  evaluation_start=1995, development=[1995,2019], holdout=[2021,2026],
                  holdout_note='Chronological retrospective holdout, inspected during initial implementation; no prospective accuracy claim.',
                  feature_horizon='Seeds at selection; schedule-derived form frozen March 1 00:00 UTC. Preliminary-round survivors are known only after those games.',
                  warmup='1985–1994 for seed models; form starts only once 100 prior paired games exist.',
                  baseline_note='seed_pick assigns 0.75 to the lower-number seed, 0.5 to ties; confidence is a fixed heuristic.',
                  calibration_note='Temperature grid [0.75,1.5] fitted only on earlier out-of-fold raw predictions; mirrored reliability bins, original game count.',
                  primary='seed', promotion_policy='Keep the interpretable seed model primary. Challengers are reported separately; no automatic holdout-based promotion.',
                  paired_uncertainty=[paired_uncertainty(records,'seed','seed_pick'),paired_uncertainty(records,'seed_curve'),paired_uncertainty(records,'form')],
                  development_metrics=summarize(1995,2019), holdout_metrics=summarize(2021,2026),
                  paired_form_development=summarize(1995,2019,form_ids), paired_form_holdout=summarize(2021,2026,form_ids),
                  by_season={str(y):summarize(y,y) for y in years if y>=1995},
                  by_round={str(r):{k:metrics([x for x in v if 2021<=x['season']<=2026 and x['round']==r]) for k,v in records.items()} for r in range(1,7)})
    live = {}
    for kind in ('seed','seed_curve','form'):
        try:
            live[kind] = calibrate(fit(rows,kind,features),prior_raw[kind])
        except ValueError:
            pass
    dump(ROOT/'artifacts/models.json',dict(as_of='2026-10-03',prediction_season=2027,primary='seed',models=live))
    dump(ROOT/'artifacts/historical_models.json',snapshots)
    dump(ROOT/'artifacts/evaluation.json',report)
    dump(ROOT/'artifacts/predictions.json',records)
    return report
