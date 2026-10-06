// Probabilities are lookup tables computed by the trained Python model.
// Only bracket path aggregation and reproducible drawing happen in this module.
const cache=new Map();
async function load(path){if(!cache.has(path))cache.set(path,fetch(new URL(`./data/${path}`,import.meta.url)).then(async r=>{if(!r.ok)throw Error(r.status===404?'This year or model has no published snapshot.':'The saved snapshot could not be loaded. Try again.');return r.json();}).catch(e=>{cache.delete(path);throw e;}));return cache.get(path);}
const rounds=['Round of 64','Round of 32','Sweet 16','Elite Eight','Final Four','Championship'];
const seedOrder=[1,16,8,9,4,13,5,12,2,15,7,10,3,14,6,11];
export function validate(field){
  if(!field||Array.isArray(field)||typeof field!=='object')throw Error('Field must be a JSON object.');
  if(!Number.isInteger(field.season)||field.season<1939||field.season>2100)throw Error('Season must be an integer year from 1939 to 2100.');
  if(field.status==='unknown')throw Error('The field is unknown. Import the announced field before forecasting.');
  const slots=field.slots;
  if(!Array.isArray(slots)||slots.length!==64||slots.some(s=>!Array.isArray(s)||![1,2].includes(s.length)))throw Error('Declare 64 main-bracket slots, each containing one team or an opening-game pair.');
  const teams=slots.flat();
  if(teams.some(t=>!t||Array.isArray(t)||typeof t!=='object'))throw Error('Each team must be a JSON object.');
  const ids=teams.map(t=>t.id);
  if(ids.some(t=>typeof t!=='string'||!t||t.length>80)||new Set(ids).size!==ids.length)throw Error('Team IDs must be unique nonempty strings of at most 80 characters.');
  for(const slot of slots){if(slot.some(t=>!Number.isInteger(t.seed)||t.seed<1||t.seed>16)||new Set(slot.map(t=>t.seed)).size!==1)throw Error('Each slot needs an integer seed 1–16; opening-game teams share the slot seed.');if(slot.some(t=>typeof t.name!=='string'||!t.name||t.name.length>100))throw Error('Each team needs a name of at most 100 characters.');}
  for(let start=0;start<64;start+=16){if(slots.slice(start,start+16).some((s,i)=>s[0].seed!==seedOrder[i]))throw Error('Each region must use bracket seed order 1,16,8,9,4,13,5,12,2,15,7,10,3,14,6,11.');}
  const opening=slots.filter(s=>s.length===2).length;
  if(teams.length!==(field.expected_teams??teams.length)||opening!==(field.expected_opening_games??opening))throw Error('Field counts disagree with the declared tournament format.');
  if(field.season===2027&&(teams.length!==76||opening!==12))throw Error('The announced 2027 format requires 76 teams and 12 opening games.');
  return teams;
}
export function simulate(field,table,kind='seed',randomSeed=2027){
  const teams=validate(field),byId=new Map(teams.map(t=>[t.id,t])),model=table.models[kind];
  if(!model)throw Error('This model has no historical training snapshot for the selected year.');
  const prob=(a,b)=>{if(kind==='form'){const i=table.teams.indexOf(a),j=table.teams.indexOf(b);if(i<0||j<0||!table.form)throw Error('Form simulation requires valid pre-tournament features for every team.');return table.form[i][j];}return table.seed[kind].probabilities[byId.get(a).seed-1][byId.get(b).seed-1];};
  let rng=(randomSeed>>>0)||0x6d2b79f5;
  const random=()=>{rng^=rng<<13;rng^=rng>>>17;rng^=rng<<5;rng>>>=0;return rng/4294967296;};
  const advancement=new Map(teams.map(t=>[t.id,Array(7).fill(0)]));let nodes=[],draw=[];const sampledOpening=[],sampled=[];
  for(const slot of field.slots){let distribution,winner;if(slot.length===1){distribution=new Map([[slot[0].id,1]]);winner=slot[0].id;}else{const [a,b]=slot.map(t=>t.id),p=prob(a,b);distribution=new Map([[a,p],[b,1-p]]);winner=random()<p?a:b;sampledOpening.push({a,b,p_a:p,winner});}for(const [team,p] of distribution)advancement.get(team)[0]=p;nodes.push(distribution);draw.push(winner);}
  for(let round=1;round<=6;round++){const nextNodes=[],nextDraw=[],drawnGames=[];for(let i=0;i<nodes.length;i+=2){const [left,right]=nodes.slice(i,i+2),out=new Map([...left.keys(),...right.keys()].map(t=>[t,0]));for(const [a,pa] of left)for(const [b,pb] of right){const p=prob(a,b);out.set(a,out.get(a)+pa*pb*p);out.set(b,out.get(b)+pa*pb*(1-p));}for(const [team,p] of out)advancement.get(team)[round]=p;const [a,b]=draw.slice(i,i+2),p=prob(a,b),winner=random()<p?a:b;drawnGames.push({a,b,p_a:p,winner});nextDraw.push(winner);nextNodes.push(out);}sampled.push({round_name:rounds[round-1],games:drawnGames});nodes=nextNodes;draw=nextDraw;}
  const odds=[...advancement].map(([team,p])=>({team,name:byId.get(team).name,seed:byId.get(team).seed,reach_round64:p[0],reach_round32:p[1],reach_sweet16:p[2],reach_elite8:p[3],reach_final4:p[4],reach_final:p[5],champion:p[6]})).sort((a,b)=>b.champion-a.champion);
  return {method:'Exact dynamic programming under fixed published pairwise probabilities; one seeded bracket draw.',season:field.season,model:kind,scope:field.scope||'Declared bracket',participants:teams.length,opening_games:field.slots.filter(s=>s.length===2).length,total_games:teams.length-1,random_seed:randomSeed,odds,sampled_opening:sampledOpening,sampled_rounds:sampled,caveat:'Assumes independent game outcomes conditional on seeds/features; uncertainty in fitted parameters is not included.'};
}
export async function request(path,options={}){
  const url=new URL(path,'https://parse-only.invalid'),q=url.searchParams;
  if(url.pathname==='/api/summary')return load('summary.json');
  if(url.pathname==='/api/team'){
    const index=await load('teams/index.json'),id=q.get('profile');
    if(!Object.hasOwn(index.profiles,id))throw Error('No published tournament history for this exact profile ID.');
    return load(`teams/${index.profiles[id].file}`);
  }
  if(options.method==='POST'){const payload=JSON.parse(options.body),table=await load('tables/2027.json');return simulate(payload.field,table,'seed',payload.rng??2027);}
  const year=Number(q.get('year')||2027),kind=q.get('model')||'seed';
  if(url.pathname==='/api/season')return load(`seasons/${year}.json`);
  if(url.pathname==='/api/predict'){
    const a=Number(q.get('a')||1),b=Number(q.get('b')||16);
    if(!Number.isInteger(a)||!Number.isInteger(b)||a<1||a>16||b<1||b>16)throw Error('Seeds must be integers from 1 to 16');
    const table=await load(`tables/${year}.json`),model=table.models[kind];if(!model)throw Error('This model has no historical training snapshot for the selected year.');
    let p,contributions=[];
    if(kind==='form'){const i=table.teams.indexOf(q.get('team_a')),j=table.teams.indexOf(q.get('team_b'));if(i<0||j<0||!table.form)throw Error('Pre-tournament features missing; use seed model');p=table.form[i][j];}
    else{const entry=table.seed[kind];p=entry.probabilities[a-1][b-1];contributions=entry.contributions[a-1][b-1].map((v,i)=>({feature:model.features[i],log_odds:v}));}
    return {p_a:p,p_b:1-p,model,contributions};
  }
  if(url.pathname==='/api/simulate'){
    const summary=await load('summary.json');if(year===2027&&summary.field.status==='unknown')throw Error('The field is unknown. Import the announced field before forecasting.');
    const season=await load(`seasons/${year}.json`),table=await load(`tables/${year}.json`);
    const field={season:year,status:'historical_main_bracket',scope:'Conditional on the 64 main-bracket participants; preliminary rounds excluded.',expected_teams:64,expected_opening_games:0,slots:season.teams.map(t=>[{id:t.id,name:t.name,seed:t.seed}])};
    return simulate(field,table,kind,Number(q.get('rng')||2027));
  }
  throw Error('Unknown API route');
}
