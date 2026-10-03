"""Exact advancement probabilities and reproducible draws on a declared bracket."""
from .model import predict
from .data import ROUNDS


class SeededRandom:
    """Portable xorshift32 draw stream shared with the static browser simulator."""
    def __init__(self,seed):
        self.state=(int(seed)&0xffffffff) or 0x6d2b79f5

    def random(self):
        x=self.state
        x^=(x<<13)&0xffffffff
        x^=x>>17
        x^=(x<<5)&0xffffffff
        self.state=x&0xffffffff
        return self.state/4294967296


def historical_field(season):
    return dict(season=season['season'], status='historical_main_bracket',
                scope='Conditional on the 64 main-bracket participants; preliminary rounds excluded.',
                expected_teams=64, expected_opening_games=0,
                slots=[[dict(id=t['id'], name=t['name'], seed=t['seed'])] for t in season['teams']])


def validate_field(field):
    if not isinstance(field,dict):
        raise ValueError('Field must be a JSON object.')
    if type(field.get('season')) is not int or not 1939<=field['season']<=2100:
        raise ValueError('Season must be an integer year from 1939 to 2100.')
    if field.get('status') == 'unknown':
        raise ValueError('The field is unknown. Import the announced field before forecasting.')
    slots = field.get('slots', [])
    if not isinstance(slots,list) or len(slots) != 64 or any(not isinstance(s,list) or len(s) not in (1,2) for s in slots):
        raise ValueError('Declare 64 main-bracket slots, each containing one team or an opening-game pair.')
    teams = [t for slot in slots for t in slot]
    if any(not isinstance(t,dict) for t in teams):
        raise ValueError('Each team must be a JSON object.')
    ids = [t.get('id') for t in teams]
    if any(not isinstance(t,str) or not t or len(t)>80 for t in ids) or len(ids)!=len(set(ids)):
        raise ValueError('Team IDs must be unique nonempty strings of at most 80 characters.')
    for slot in slots:
        seeds = [t.get('seed') for t in slot]
        if any(type(s) is not int or not 1<=s<=16 for s in seeds) or len(set(seeds))!=1:
            raise ValueError('Each slot needs an integer seed 1–16; opening-game teams share the slot seed.')
        if any(not isinstance(t.get('name'),str) or not t['name'] or len(t['name'])>100 for t in slot):
            raise ValueError('Each team needs a name of at most 100 characters.')
    seed_order = [1,16,8,9,4,13,5,12,2,15,7,10,3,14,6,11]
    for start in range(0,64,16):
        if [s[0]['seed'] for s in slots[start:start+16]] != seed_order:
            raise ValueError('Each region must use bracket seed order 1,16,8,9,4,13,5,12,2,15,7,10,3,14,6,11.')
    opening = sum(len(s)==2 for s in slots)
    expected = field.get('expected_teams',len(teams))
    expected_opening = field.get('expected_opening_games',opening)
    if len(teams)!=expected or opening!=expected_opening:
        raise ValueError('Field counts disagree with the declared tournament format.')
    if field.get('season') == 2027 and (len(teams)!=76 or opening!=12):
        raise ValueError('The announced 2027 format requires 76 teams and 12 opening games.')
    return teams


def simulate(field, model, team_features=None, random_seed=2027):
    teams = validate_field(field)
    by_id = {t['id']:t for t in teams}
    feats = team_features or {}
    if model['kind']=='form' and any(t['id'] not in feats for t in teams):
        raise ValueError('Form simulation requires valid pre-tournament features for every team.')
    def probability(a,b):
        return predict(model,by_id[a]['seed'],by_id[b]['seed'],feats.get(a),feats.get(b))
    rng = SeededRandom(random_seed)
    advancement = {t['id']:[0.]*7 for t in teams}
    nodes, draw, sampled = [], [], []
    opening_draw = []
    for slot in field['slots']:
        if len(slot)==1:
            distribution = {slot[0]['id']:1.}
            winner = slot[0]['id']
        else:
            a,b = [t['id'] for t in slot]
            p = probability(a,b)
            distribution = {a:p,b:1-p}
            winner = a if rng.random()<p else b
            opening_draw.append(dict(a=a,b=b,p_a=p,winner=winner))
        for team,p in distribution.items():
            advancement[team][0]=p
        nodes.append(distribution)
        draw.append(winner)
    for round_number, label in enumerate(ROUNDS,1):
        next_nodes, next_draw, drawn_games = [], [], []
        for i in range(0,len(nodes),2):
            left,right = nodes[i:i+2]
            out = {t:0. for t in (*left,*right)}
            for a,pa in left.items():
                for b,pb in right.items():
                    p = probability(a,b)
                    out[a] += pa*pb*p
                    out[b] += pa*pb*(1-p)
            for team,p in out.items():
                advancement[team][round_number]=p
            a,b = draw[i:i+2]
            p = probability(a,b)
            winner = a if rng.random()<p else b
            drawn_games.append(dict(a=a,b=b,p_a=p,winner=winner))
            next_draw.append(winner)
            next_nodes.append(out)
        sampled.append(dict(round_name=label,games=drawn_games))
        nodes,draw = next_nodes,next_draw
    odds = [dict(team=t, name=by_id[t]['name'], seed=by_id[t]['seed'],
                 reach_round64=p[0], reach_round32=p[1], reach_sweet16=p[2], reach_elite8=p[3],
                 reach_final4=p[4], reach_final=p[5], champion=p[6]) for t,p in advancement.items()]
    odds.sort(key=lambda x:x['champion'],reverse=True)
    return dict(method='Exact dynamic programming under fixed pairwise probabilities; one seeded bracket draw.',
                season=field['season'], model=model['kind'], scope=field.get('scope','Declared bracket'),
                participants=len(teams), opening_games=sum(len(s)==2 for s in field['slots']),
                total_games=len(teams)-1, random_seed=random_seed, odds=odds,
                sampled_opening=opening_draw, sampled_rounds=sampled,
                caveat='Assumes independent game outcomes conditional on seeds/features; uncertainty in fitted parameters is not included.')
