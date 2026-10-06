// Read saved evidence and coverage. This view never fits or selects a model.
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=value=>value==null?'—':Number(value).toLocaleString('en-US');
const metric=value=>value==null?'—':Number(value).toFixed(5);
const forecasters={coin:'50/50',seed_pick:'Fixed seed heuristic',seed:'Seed logistic · primary',seed_curve:'Seed curve · challenger',form:'Pre-March form · challenger'};

function coverageCard(title,value,note){
  return `<div class="coverage-card"><h3>${title}</h3><strong>${value}</strong><p class="note">${note}</p></div>`;
}

function seasonMarkup(season,summary){
  const played=season.games.filter(g=>g.status==='played');
  const noContests=season.games.filter(g=>g.status==='no_contest').length;
  const enriched=played.filter(g=>g.score_a!=null&&g.score_b!=null&&g.date_utc).length;
  const featureCount=season.teams.filter(t=>season.features?.[t.id]).length;
  const model=season.model,year=season.season;
  const coverage=summary.coverage?.seasons.find(s=>s.season===year);
  const cutoff=coverage?.cutoff_utc;
  const metrics=summary.evaluation.by_season[year];
  const [start,end]=summary.evaluation.holdout;
  const phase=metrics?(year>=start&&year<=end?'Rolling holdout':'Development evaluation'):'Warm-up · unscored';
  const through=model?Math.max(...model.train_seasons):null;
  return `<div class="insight-heading"><div><p class="eyebrow">${phase}</p><h3>${year} tournament</h3></div><a class="button" id="insight-archive" href="#archive">Open ${year} bracket →</a></div>
    <div class="coverage-grid">
      ${coverageCard('Archive labels',`${number(played.length)} played games`,`${number(season.games.length)} advancements.${noContests?` ${number(noContests)} no-contest advancement excluded from fitting and evaluation.`:''}`)}
      ${coverageCard('Scores & dates',`${number(enriched)} / ${number(played.length)}`,enriched?'Played games with both scores and a UTC date.':'Scores and dates are absent from this bundled season.')}
      ${coverageCard('Pre-March form',`${number(featureCount)} / ${number(season.teams.length)} teams`,featureCount?`Frozen ${esc(cutoff?.slice(0,10)??'March 1')} at 00:00 UTC. Coverage does not imply a trained form snapshot.`:'No bundled form features. Seed probabilities do not use these statistics.')}
    </div>
    <dl class="snapshot-grid"><div><dt>Primary model training</dt><dd>${model?`${number(model.n_train)} earlier games · through ${through}`:'— · no prediction snapshot'}</dd></div><div><dt>Primary model calibration</dt><dd>${model?.calibration_n?`${number(model.calibration_n)} earlier predictions · through ${model.calibration_through}`:model?'No prior calibration fit · temperature 1':'— · no prediction snapshot'}</dd></div></dl>
    <p class="note">${model?'This saved annual snapshot uses only earlier tournaments for fitting and calibration. It is a retrospective evaluation; later rolling years can learn from earlier holdout outcomes.':'This season belongs to the training warm-up era. An archived result does not imply an evaluated prediction.'}</p>
    <p class="insight-scroll-hint note">On narrow screens, scroll the table → to compare scores.</p><div class="table-scroll" tabindex="0" role="region" aria-label="Saved tournament evaluation, scroll horizontally to compare scores"><table><caption>Saved ${year} evaluation · lower Brier and log loss are better</caption><thead><tr><th>Forecaster</th><th class="numeric">Scored games</th><th class="numeric">Brier ↓</th><th class="numeric">Log loss ↓</th></tr></thead><tbody>${Object.entries(forecasters).map(([kind,name])=>{const m=metrics?.[kind];return `<tr><th scope="row">${name}</th><td class="numeric">${number(m?.n)}</td><td class="numeric">${metric(m?.brier)}</td><td class="numeric">${metric(m?.log_loss)}</td></tr>`;}).join('')}</tbody></table></div>
    <p class="note insight-footnote">${season.available_models?.includes('form')?'The form challenger has an earlier training snapshot for this season.':featureCount?'Form features exist, but the form challenger has too few earlier feature-covered games for a training snapshot.':'The form challenger is unavailable for this season.'} A dash means no recorded evaluation; it is never a zero score. One tournament does not justify promoting a challenger. The form challenger did not improve the primary seed model’s Brier or log loss across the full saved holdout.</p>`;
}

export function mountSeasonInsights(container,{summary,request,initialYear,onOpenArchive}){
  const cancelled=summary.provenance.cancelled_years??[];
  const years=[...new Set([...summary.years,...cancelled])].sort((a,b)=>b-a);
  const selected=years.includes(initialYear)?initialYear:summary.years[0];
  container.innerHTML=`<div class="insight-toolbar"><div><h2 id="season-insights-title">Season evidence</h2><p class="note">Inspect coverage and the model’s information horizon before opening a historical bracket.</p></div><label for="insight-year">Tournament year<select id="insight-year">${years.map(y=>`<option value="${y}" ${y===selected?'selected':''}>${y}${cancelled.includes(y)?' · cancelled':''}</option>`).join('')}</select></label></div><div id="insight-status" class="statusline" role="status" aria-live="polite"></div><div id="insight-content"></div><details><summary>How to read this evidence</summary><p class="note">Brier averages squared probability error; log loss penalizes assigning very little probability to the actual winner. Lower is better for both. These scores describe saved historical game predictions, not a guarantee of future accuracy.</p><p class="note">Coverage is measured separately for played results, score/date enrichment and pre-March team features. Main-bracket experiments are conditional on preliminary-round survivors. Earlier history remains missing from the archive; ${cancelled.map(esc).join(', ')} was cancelled. Injuries, rosters and market prices are not modeled.</p></details>`;
  const select=container.querySelector('#insight-year');
  const status=container.querySelector('#insight-status');
  const content=container.querySelector('#insight-content');
  let revision=0;
  async function load(){
    const year=Number(select.value),current=++revision;
    content.innerHTML='';content.setAttribute('aria-busy','true');
    status.textContent=`Loading ${year} evidence…`;
    try{
      if(cancelled.includes(year)){
        content.innerHTML=`<div class="cancelled-season"><span class="tag">TOURNAMENT CANCELLED</span><h3>${year} · no tournament played</h3><p class="muted">There is no bracket, game evaluation or tournament feature snapshot for this year. This is separate from years missing from the archive.</p></div>`;
      }else{
        const season=await request(`/api/season?year=${year}`);
        if(current!==revision||!container.isConnected)return;
        content.innerHTML=seasonMarkup(season,summary);
        content.querySelector('#insight-archive').addEventListener('click',()=>onOpenArchive(year));
      }
      status.textContent=`${year} evidence loaded.`;
    }catch(error){
      if(current!==revision||!container.isConnected)return;
      status.textContent=`Could not load ${year} evidence: ${error.message}`;
      const retry=document.createElement('button');retry.textContent='Retry season evidence';retry.addEventListener('click',load);content.append(retry);
    }finally{
      if(current===revision)content.removeAttribute('aria-busy');
    }
  }
  select.addEventListener('change',load);
  load();
}
