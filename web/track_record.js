const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const percent=value=>value==null?'Not yet scored':`${value.toFixed(1)}%`;
const fraction=value=>`${value.correct} / ${value.settled}`;
const date=value=>value.slice(0,10);

export function recordStrip(record){
  if(!record)return '';
  return `<a class="record-strip" href="#record"><span><strong>${percent(record.historical.accuracy_pct)}</strong> <span>${fraction(record.historical)} correct</span></span><span>Historical backtest · ${record.holdout.join('–')}<small>Published forecasts: ${percent(record.prospective.accuracy_pct)} · Track record →</small></span></a>`;
}

function chart(points){
  const start=Date.parse(points[0].date_utc),span=Math.max(1,Date.parse(points.at(-1).date_utc)-start);
  const x=p=>80+(Date.parse(p.date_utc)-start)/span*580,y=value=>230-value*1.9;
  const line=(group,key)=>group.map(p=>`${x(p)},${y(p[key].accuracy_pct)}`).join(' ');
  const seasons=[...new Set(points.map(p=>p.season))];
  return `<div class="record-chart-scroll" role="region" aria-label="Accuracy timeline with calendar dates and 0 to 100 percent axis" tabindex="0"><svg class="record-chart" viewBox="0 0 720 280" role="img" aria-labelledby="record-chart-title record-chart-desc"><title id="record-chart-title">Seed baseline accuracy by UTC calendar date</title><desc id="record-chart-desc">Vertical axis 0 to 100 percent. Solid line: cumulative game picks. Dashed line: last 20 games, reset each tournament. Straight lines join observed weeks; gaps have no games. Exact counts for every point are in the calendar table below.</desc>${[0,25,50,75,100].map(value=>`<line class="grid" x1="80" y1="${y(value)}" x2="660" y2="${y(value)}"/><text x="4" y="${y(value)+4}">${value}%</text>`).join('')}<polyline class="record-cumulative" points="${line(points,'cumulative')}"/>${seasons.map(season=>`<polyline class="record-recent" points="${line(points.filter(p=>p.season===season),'recent')}"/>`).join('')}${points.map((p,i)=>`<circle class="record-dot" data-point="${i}" cx="${x(p)}" cy="${y(p.cumulative.accuracy_pct)}" r="3"/>`).join('')}${seasons.map(season=>{const p=points.find(p=>p.season===season);return `<text x="${x(p)}" y="256" text-anchor="middle">${date(p.date_utc).slice(0,7)}</text>`;}).join('')}<text x="290" y="278">Calendar date · UTC</text></svg></div>`;
}

export async function mountTrackRecord(container,{request,params,isCurrent}){
  let report,view=params.get('view')==='prospective'?'prospective':'historical',season=params.get('season')||'all';
  let point=Number(params.get('point')),page=Math.max(0,Number(params.get('page'))||0),all=false,ownedHash=location.hash;
  const current=()=>isCurrent()&&container.isConnected&&location.hash===ownedHash;
  const data=()=>season==='all'?report[view]:{...report[view].seasons[season],records:report[view].records.filter(row=>String(row.season)===season)};
  const sync=()=>{
    if(!current())return;
    history.replaceState(null,'',`#record?${new URLSearchParams({view,season,point,page})}`);ownedHash=location.hash;
  };
  const selectPoint=index=>{
    const points=data().points;point=Math.max(0,Math.min(points.length-1,index));
    const p=points[point];if(!p)return;
    const control=container.querySelector('#record-point');control.value=point;
    control.setAttribute('aria-valuetext',`${p.week}, through ${date(p.date_utc)}, cumulative ${fraction(p.cumulative)} correct, ${percent(p.cumulative.accuracy_pct)}`);
    container.querySelector('#record-point-detail').innerHTML=`<strong>${p.week} · ${p.week_start} to ${p.week_end} UTC</strong><span>Through ${date(p.date_utc)}: cumulative <b>${fraction(p.cumulative)} correct · ${percent(p.cumulative.accuracy_pct)}</b>.</span><span>This week: ${fraction(p.weekly)} correct. Recent form: <b>${fraction(p.recent)} correct · ${percent(p.recent.accuracy_pct)}</b>, ${date(p.recent_start)} to ${date(p.recent_end)}.</span>`;
    container.querySelectorAll('[data-point]').forEach(dot=>dot.classList.toggle('selected',Number(dot.dataset.point)===point));sync();
  };
  const ledger=()=>{
    const rows=data().records,limit=20,pages=Math.max(1,Math.ceil(rows.length/limit));page=Math.min(pages-1,Math.floor(page));
    const ordered=[...rows].reverse(),visible=all?ordered:ordered.slice(page*limit,(page+1)*limit);
    container.querySelector('#record-ledger').innerHTML=`<h2>Pick beside result</h2><p class="note">${rows.length} eligible ${view==='historical'?'retrospective':'published pre-event'} game picks, newest first. ${all?'Showing all rows.':`Showing ${page*limit+1}–${Math.min((page+1)*limit,rows.length)}.`}</p>
      <div class="record-pagination"><button id="record-prev" ${page===0||all?'disabled':''}>Previous picks</button><button id="record-next" ${page===pages-1||all?'disabled':''}>Next picks</button><button id="record-all">${all?'Show 20 per page':`Show all ${rows.length}`}</button></div>
      <ol class="record-games" aria-label="Scored outcome picks">${visible.map(row=>`<li class="record-game" data-record-id="${esc(row.game_id)}" data-correct="${row.correct}">
        <div class="record-game-heading"><p><time datetime="${esc(row.date_utc)}">${date(row.date_utc)}</time> · ${esc(row.round_name)}</p><h3>${esc(row.name_a)} vs ${esc(row.name_b)}</h3></div>
        <dl class="record-outcomes"><div><dt>Model pick</dt><dd>${esc(row.pick_name)}<small>${percent((row.pick===row.a?row.p_a:1-row.p_a)*100)} · seed baseline</small></dd></div><div><dt>Actual winner</dt><dd>${esc(row.winner_name)}</dd></div></dl>
        <p class="record-verdict">${row.correct?'Correct · 1':'Incorrect · 0'}</p>
        <details class="record-pick-audit"><summary>Pick details</summary><p>Game ${esc(row.game_id)}<br>${esc(row.date_utc)}<br>Saved P(A): ${percent(row.p_a*100)}<br>Train through ${row.train_through??'—'}; calibration through ${row.calibration_through??'—'}.<br>${view==='historical'?'Retrospective record; publication time unknown.':`Issued ${esc(row.issued_at)}; published ${esc(row.published_at)}.`}</p>${row.result_source?`<a href="${esc(row.result_source)}" rel="noreferrer">Archived result source</a>`:''}</details>
      </li>`).join('')}</ol>`;
    container.querySelector('#record-prev').onclick=()=>{page--;ledger();sync();container.querySelector('#record-next').focus({preventScroll:true});};
    container.querySelector('#record-next').onclick=()=>{page++;ledger();sync();container.querySelector('#record-prev').focus({preventScroll:true});};
    container.querySelector('#record-all').onclick=()=>{all=!all;ledger();sync();container.querySelector('#record-all').focus({preventScroll:true});};
  };
  const timeline=selected=>{
    const points=selected.points;
    return `<details class="panel record-timeline"><summary>Calendar trend & exact counts</summary><h2>Accuracy over calendar time</h2><p class="record-legend"><span>━ Cumulative</span><span>┄ Recent form · last ${report.recent_games} games</span></p><p class="note">Counts cover the selected tournament season or all holdout tournaments. Recent form resets each tournament; startup windows use their actual game count. UTC weeks contain only eligible games. Lines join observed weeks; off-season gaps have no games.</p>${chart(points)}
      <label for="record-point">Inspect a calendar point<input type="range" id="record-point" min="0" max="${points.length-1}" step="1" value="${point}"></label><div class="record-point-buttons"><button data-point-step="-1">Earlier week</button><button data-point-step="1">Later week</button></div><output id="record-point-detail" aria-live="polite"></output>
      <details class="record-calendar"><summary>All calendar points · exact counts</summary><div class="table-scroll" role="region" tabindex="0" aria-label="Calendar accuracy table, scroll horizontally for recent form"><table><caption>Every observed UTC week; cumulative totals pool game counts within this selection</caption><thead><tr><th>Week / through date</th><th>Week correct / settled</th><th>Cumulative correct / settled</th><th>Cumulative %</th><th>Recent correct / settled</th><th>Recent % / dates</th></tr></thead><tbody>${points.map(p=>`<tr><td>${p.week}<br>${date(p.date_utc)}</td><td>${fraction(p.weekly)}</td><td>${fraction(p.cumulative)}</td><td>${percent(p.cumulative.accuracy_pct)}</td><td>${fraction(p.recent)}</td><td>${percent(p.recent.accuracy_pct)}<br>${date(p.recent_start)} to ${date(p.recent_end)}</td></tr>`).join('')}</tbody></table></div></details></details>`;
  };
  const draw=focus=>{
    const selected=data(),historical=view==='historical',points=selected.points,coverage=selected.coverage;
    if(!params.has('point')||!Number.isInteger(point)||point<0||point>=points.length)point=Math.max(0,points.length-1);
    const years=Object.keys(report[view].seasons).sort((a,b)=>Number(b)-Number(a));
    const period=season==='all'?(historical?report.holdout.join('–'):'ALL VERIFIED FORECAST SEASONS'):season;
    container.innerHTML=`<section class="track-record"><p class="eyebrow">MEN’S NCAA DIVISION I · SEED BASELINE</p><h1>Track record</h1>
      <div class="segmented record-tabs" role="group" aria-label="Track record source"><button data-record-view="historical" aria-pressed="${historical}">Historical backtest</button><button data-record-view="prospective" aria-pressed="${!historical}">Published forecasts</button></div>
      <label class="record-season" for="record-season">Tournament season<select id="record-season"><option value="all">${historical?`All holdout tournaments · ${report.holdout.join('–')}`:'All available tournament seasons'}</option>${years.map(year=>`<option value="${year}" ${season===year?'selected':''}>${year} tournament</option>`).join('')}</select></label>
      <section class="panel record-score" aria-label="${historical?'Historical held-out backtest':'Published pre-event forecasts'} accuracy"><p class="eyebrow">${historical?`${period} · HISTORICAL HELD-OUT BACKTEST`:`${period} · PRE-EVENT PUBLISHED FORECASTS`}</p><strong id="record-accuracy">${percent(selected.totals.accuracy_pct)}</strong><p id="record-count"><b>${fraction(selected.totals)}</b> correct picks / settled eligible games</p>
      <p class="note">${historical?'Retrospective, not a published pre-event record. Training and calibration use earlier seasons; this holdout was inspected during implementation.':selected.totals.settled?'Only verified seed-model picks issued and published before their recorded event are scored.':'No verified pre-event publication ledger is bundled. Historical snapshots stay separate.'}</p>
      <p class="record-unit">Game-result picks on actual matchups. Filled-bracket advancement accuracy is not recorded.</p></section>
      <section class="record-coverage" aria-label="Selected game coverage"><h2>What is counted</h2><p><b>${coverage.eligible_games}</b> scored picks from <b>${coverage.settled_results}</b> known settled played results · ${coverage.archived_games} archived main-bracket games.</p><p><span data-coverage="no-contests">${coverage.no_contests} no-contest excluded</span> · <span data-coverage="missing-picks">${coverage.missing_or_ineligible_picks} settled results without an eligible pick</span> · <span data-coverage="unavailable-results">${coverage.unavailable_results} unavailable or unsettled results</span>.</p></section>
      ${selected.totals.settled?`<section id="record-ledger" class="panel"></section>${timeline(selected)}`:`<div class="panel record-empty"><h2>Not yet scored</h2><p>No eligible settled ${historical?'backtest picks':'pre-event published picks'} are available for this selection. An empty record is not 0% accuracy.</p></div>`}
      <details class="record-method"><summary>Scoring, scope & source audit</summary><p>${esc(report.rule)} Each correct pick earns 1, each incorrect pick 0. ${esc(report.order)} ${esc(report.recent_rule)} No accuracy guarantee or AI success claim follows from this record.</p><p>Game accuracy counts one pick per actual archived matchup, including later rounds. It does not score the advancement slots in a filled bracket. No archived pre-event filled-bracket ledger is bundled; that separate record is unavailable. Exact-score forecasts are not produced, so no score-error metric is claimed.</p><p>Historical 64-team main brackets are conditional on First Four survivors. Preliminary games and losers are absent. No-contests are excluded, not incorrect picks. The 2027 field is unannounced and has no scored predictions here.</p><p>A known played result without an eligible pick is unscored, not incorrect. Unavailable results include missing event times, future events, and unplayed or invalid outcomes. Coverage counts unique games; source-row rejection counts may include multiple rejected rows for one event.</p><p>Prospective eligibility requires an explicit saved seed-model pick, issued and published timestamps strictly before the known event time, and a settled played result. Missing/late times and duplicate event rows remain excluded; no earliest/latest row is selected. Full ${historical?'historical':'prospective'} source exclusion counts: <code>${esc(JSON.stringify(report[view].excluded))}</code>.</p><p>Snapshot as of ${esc(report.as_of)}. Model artifacts record training years, not dated public releases; no version markers have been invented.</p><p>Legacy probability evaluation uses half-credit for exact 50–50 ties: ${percent(report.legacy_half_credit_accuracy==null?null:report.legacy_half_credit_accuracy*100)} across the full holdout. That convention is separate from the integer pick scoring above. <a href="#evidence">Probability metrics & calibration →</a></p><h3>Existing source files · SHA-256</h3><ul>${Object.entries(report.sources_sha256).map(([name,hash])=>`<li><code>${esc(name)}</code><br><code>${esc(hash)}</code></li>`).join('')}</ul><a href="#about">Attribution & data coverage →</a></details><a class="button" href="#home">Back to brackets →</a></section>`;
    container.querySelectorAll('[data-record-view]').forEach(button=>button.onclick=()=>{view=button.dataset.recordView;if(season!=='all'&&!Object.hasOwn(report[view].seasons,season))season='all';page=0;all=false;point=Math.max(0,data().points.length-1);draw(`[data-record-view="${view}"]`);sync();});
    container.querySelector('#record-season').onchange=event=>{season=event.target.value;page=0;all=false;point=Math.max(0,data().points.length-1);draw('#record-season');sync();};
    if(selected.totals.settled){ledger();selectPoint(point);container.querySelector('#record-point').oninput=event=>selectPoint(Number(event.target.value));container.querySelectorAll('[data-point-step]').forEach(button=>button.onclick=()=>selectPoint(point+Number(button.dataset.pointStep)));}
    else sync();
    if(focus)container.querySelector(focus)?.focus({preventScroll:true});
  };
  const load=async()=>{
    const retryFocused=document.activeElement===container.querySelector('#record-retry');
    container.innerHTML='<div class="loading" role="status">Loading saved track record…</div>';
    try{
      const loaded=await request('/api/track-record');if(!current())return;report=loaded;
      if(season!=='all'&&!Object.hasOwn(report[view].seasons,season))season='all';
      draw(retryFocused?'[data-record-view="historical"]':null);
    }catch(error){if(current()){container.innerHTML=`<section class="panel"><h1>Track record unavailable</h1><p role="alert">${esc(error.message)}</p><button id="record-retry">Retry track record</button> <a href="#home">Back to brackets</a></section>`;container.querySelector('#record-retry').onclick=load;if(retryFocused)container.querySelector('#record-retry').focus({preventScroll:true});}}
  };
  await load();
}
