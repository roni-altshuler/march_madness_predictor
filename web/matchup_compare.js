// Compare saved forecasts for one recorded game; no fitting or model selection.
import {archiveHref,teamHref} from './team_profiles.js';
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=value=>value==null?'—':`${(100*value).toFixed(1)}%`;
const models=[['seed','Seed baseline','Primary','Seeds only.'],['seed_curve','Seed curve','Challenger','Adds a log-seed ratio.'],['form','Pre-March form','Challenger','Adds Elo, win rate and mean margin frozen March 1, 00:00 UTC.']];

export function unavailableReason(season,game,kind){
  if(game.status==='no_contest')return 'No contest: no played-game comparison or evaluation.';
  if(!season.available_models.includes(kind))return kind==='form'&&season.features[game.a]&&season.features[game.b]?'Form features exist, but no earlier-trained form snapshot is available.':'No saved earlier-trained snapshot for this model and year.';
  if(kind==='form'&&(!season.features[game.a]||!season.features[game.b]))return 'Pre-March features are missing for one or both teams.';
  return null;
}

export function comparisonRows(season,game,forecasts,swapped=false){
  const baseline=forecasts.seed;
  return models.map(([kind,name,role,note])=>{
    const missing=unavailableReason(season,game,kind),forecast=missing?null:forecasts[kind];
    if(!missing&&!forecast)throw Error('A saved forecast is missing. Try loading this comparison again.');
    if(forecast){
      const {p_a,p_b,model}=forecast;
      if(!Number.isFinite(p_a)||!Number.isFinite(p_b)||p_a<0||p_a>1||p_b<0||p_b>1||Math.abs(p_a+p_b-1)>1e-9)throw Error('The saved probabilities could not be verified.');
      if(!model.train_seasons?.length||model.train_seasons.some(year=>year>=season.season))throw Error('The saved training horizon must precede this tournament.');
    }
    const p=forecast?(swapped?forecast.p_b:forecast.p_a):null;
    const reference=baseline?(swapped?baseline.p_b:baseline.p_a):null;
    return {kind,name,role,note,missing,p_a:p,p_b:forecast?(swapped?forecast.p_a:forecast.p_b):null,
      gap:kind==='seed'||p==null||reference==null?null:(p-reference)*100,
      through:forecast?Math.max(...forecast.model.train_seasons):null,n_train:forecast?.model.n_train??null};
  });
}

export function mountMatchupComparison(container,{summary,request,initialYear,initialGame,initialSide='a'}){
  const cancelled=summary.provenance.cancelled_years??[],years=[...new Set([...summary.years,...cancelled])].sort((a,b)=>b-a);
  const selected=years.includes(initialYear)?initialYear:summary.years[0];
  container.innerHTML=`<div class="compare-heading"><div><p class="eyebrow">ONE RECORDED GAME · MODEL COMPARISON</p><h2 id="compare-title">Recorded matchup comparison</h2><p class="note">Inspect how the baseline and challengers viewed the same matchup. Missing annual snapshots stay explicit.</p></div><span class="compare-primary-label">SEED BASELINE · PRIMARY</span></div>
    <div class="compare-controls"><label for="compare-year">Tournament year<select id="compare-year">${years.map(y=>`<option value="${y}" ${y===selected?'selected':''}>${y}${cancelled.includes(y)?' · cancelled':''}</option>`).join('')}</select></label><label for="compare-game">Recorded matchup<select id="compare-game" disabled><option>Loading games…</option></select></label></div>
    <div id="compare-status" class="statusline" role="status" aria-live="polite"></div><div class="compare-actions"><button id="compare-swap" disabled aria-pressed="false">Swap team sides</button><a id="compare-evidence" href="#evidence?year=${selected}">Inspect season evidence →</a></div><div id="compare-content"></div>
    <p class="note compare-boundary">These are retrospective probabilities for archived main-bracket participants, conditional on preliminary-round survivors. Seeds were known at selection; later-round matchup identities became known as the tournament progressed. Model gaps describe different assumptions, not uncertainty intervals or evidence of better accuracy. The seed baseline stays primary; the form challenger did not improve the full saved holdout. Injuries, rosters and market prices are not modeled.</p>`;
  const yearSelect=container.querySelector('#compare-year'),gameSelect=container.querySelector('#compare-game'),swap=container.querySelector('#compare-swap'),status=container.querySelector('#compare-status'),content=container.querySelector('#compare-content');
  let season=null,game=null,forecasts={},swapped=false,revision=0;
  const current=version=>version===revision&&container.isConnected;
  function updateUrl(year,id,side){
    const url=new URL(location.href),query=new URLSearchParams(url.hash.split('?')[1]);
    query.set('compare_year',year);
    if(id)query.set('compare_game',id);else query.delete('compare_game');
    if(side)query.set('compare_side','b');else query.delete('compare_side');
    url.hash=`matchup?${query}`;history.replaceState(null,'',url);
  }
  function loading(note){
    forecasts={};swap.disabled=true;swap.setAttribute('aria-pressed',String(swapped));content.setAttribute('aria-busy','true');
    content.innerHTML=`<div class="insight-placeholder"><span class="loading-track" aria-hidden="true"></span><p class="note">${note}</p></div>`;
  }
  function showError(error,retry){
    content.removeAttribute('aria-busy');status.textContent='Comparison could not be loaded.';
    content.innerHTML=`<div class="insight-empty" role="alert"><h3>Comparison unavailable</h3><p class="muted">${esc(error.message)}</p><button id="compare-retry">Retry comparison</button></div>`;
    content.querySelector('#compare-retry').addEventListener('click',retry);
  }
  function render(){
    const rows=comparisonRows(season,game,forecasts,swapped),byId=new Map(season.teams.map(t=>[t.id,t]));
    const [a,b]=(swapped?[game.b,game.a]:[game.a,game.b]).map(id=>byId.get(id));
    const origin={year:season.season,region:game.round>=5?4:Math.floor(byId.get(game.a).slot/16),game:game.id,view:'actual'};
    const team=record=>`<a href="${esc(teamHref(record.profile_id,origin))}" title="Explore recorded tournament history">${esc(record.name)}</a>`;
    const scores=swapped?[game.score_b,game.score_a]:[game.score_a,game.score_b];
    content.innerHTML=`<div class="compare-game-heading"><div><p class="eyebrow">${season.season} · ${esc(game.round_name)}</p><h3>${team(a)} <span>vs</span> ${team(b)}</h3><p class="note">Seeds ${a.seed} & ${b.seed} · ${game.status==='no_contest'?'Recorded advancement':'Recorded winner'}: <strong>${esc(byId.get(game.winner).name)}</strong> · score ${scores.some(score=>score==null)?'—':`${scores[0]}–${scores[1]}`} · ${game.date_utc?esc(game.date_utc.slice(0,10))+' UTC':'date —'}</p></div><a class="button" id="compare-archive" href="${esc(archiveHref(origin))}">Open actual bracket →</a></div>
      <div class="forecast-cards">${rows.map(row=>`<article class="forecast-card ${row.kind==='seed'?'forecast-primary':''}" data-forecast="${row.kind}"><div class="forecast-heading"><h4>${row.name}</h4><span>${row.role}</span></div><p class="note">${row.note}</p><div class="forecast-pair"><div><span>${esc(a.name)}</span><strong data-probability="a">${pct(row.p_a)}</strong></div><div><span>${esc(b.name)}</span><strong data-probability="b">${pct(row.p_b)}</strong></div></div>${row.p_a==null?'':`<div class="forecast-strip" aria-hidden="true"><span style="width:${100*row.p_a}%"></span></div>`}<p class="forecast-gap">${row.missing?esc(row.missing):row.kind==='seed'?'Reference forecast':`${row.gap>=0?'+':''}${row.gap.toFixed(1)} percentage points vs baseline for ${esc(a.name)}`}</p><p class="note forecast-horizon">${row.through==null?'Training horizon —':`Trained through ${row.through} · ${row.n_train.toLocaleString('en-US')} earlier games`}</p></article>`).join('')}</div>`;
    content.removeAttribute('aria-busy');swap.disabled=false;swap.setAttribute('aria-pressed',String(swapped));
    status.textContent=`${season.season} ${game.status==='no_contest'?'no-contest record':'saved matchup comparison'} loaded.`;
  }
  async function loadGame(id,side=false){
    const version=++revision;game=season.games.find(record=>record.id===id)||season.games[0];swapped=side;
    gameSelect.value=game.id;updateUrl(season.season,game.id,swapped);
    loading('Retrieving saved probabilities for this recorded matchup.');status.textContent=`Loading ${season.season} comparison…`;
    try{
      const entries=await Promise.all(models.filter(([kind])=>!unavailableReason(season,game,kind)).map(async([kind])=>{
        const query=new URLSearchParams({year:season.season,model:kind,a:game.seed_a,b:game.seed_b,team_a:game.a,team_b:game.b});
        return [kind,await request(`/api/predict?${query}`)];
      }));
      if(!current(version))return;
      forecasts=Object.fromEntries(entries);render();
    }catch(error){if(current(version))showError(error,()=>loadGame(game.id,swapped));}
  }
  async function loadYear(preferredGame=null,side=false){
    const year=Number(yearSelect.value),version=++revision;
    season=null;game=null;swapped=side;gameSelect.disabled=true;gameSelect.innerHTML='<option>Loading games…</option>';
    updateUrl(year,preferredGame,side);container.querySelector('#compare-evidence').href=`#evidence?year=${year}`;
    loading('Retrieving the recorded tournament and its saved model availability.');status.textContent=`Loading ${year} comparison…`;
    if(cancelled.includes(year)){
      gameSelect.innerHTML='<option>No tournament played</option>';content.removeAttribute('aria-busy');
      content.innerHTML=`<div class="cancelled-season"><span class="tag">TOURNAMENT CANCELLED</span><h3>${year} · no recorded matchups</h3><p class="muted">There is no tournament, game probability comparison or model evaluation for this year. Choose an archived tournament above.</p></div>`;
      status.textContent=`${year} tournament cancelled.`;return;
    }
    try{
      const loaded=await request(`/api/season?year=${year}`);
      if(!current(version))return;
      if(!loaded.games.length)throw Error('No recorded matchups are bundled for this tournament.');
      season=loaded;const names=new Map(season.teams.map(t=>[t.id,t.name]));
      gameSelect.innerHTML=season.games.map(record=>`<option value="${esc(record.id)}">${esc(record.round_name)} · ${esc(names.get(record.a))} vs ${esc(names.get(record.b))}${record.status==='no_contest'?' · no contest':''}</option>`).join('');
      gameSelect.disabled=false;await loadGame(preferredGame,side);
    }catch(error){if(current(version)){gameSelect.innerHTML='<option>Games unavailable</option>';showError(error,()=>loadYear(preferredGame,side));}}
  }
  yearSelect.addEventListener('change',()=>loadYear());gameSelect.addEventListener('change',()=>loadGame(gameSelect.value));
  swap.addEventListener('click',()=>{swapped=!swapped;updateUrl(season.season,game.id,swapped);render();});
  if(initialGame){yearSelect.focus({preventScroll:true});container.scrollIntoView({block:'start'});}
  loadYear(initialGame,initialSide==='b');
}
