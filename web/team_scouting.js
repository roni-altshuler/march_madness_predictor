// Descriptive scouting from frozen form and earlier appearances; never a model input.
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (value, digits=1) => value == null ? '—' : value.toLocaleString('en-US', {minimumFractionDigits:digits, maximumFractionDigits:digits});
const signed = value => value == null ? '—' : `${value >= 0 ? '+' : ''}${number(value, 2)}`;
const windowValue = value => ['3','5','all'].includes(String(value)) ? String(value) : '5';

export function scoutingSummary(profile, year, window='5') {
  window = windowValue(window);
  const earlier = profile.appearances.filter(record => record.year < year).sort((a,b) => b.year-a.year);
  const records = window === 'all' ? earlier : earlier.slice(0, Number(window));
  let scoredGames=0, recordedWins=0, expectedWins=0, playedGames=0, noContests=0;
  for (const record of records) {
    playedGames += record.played_wins + record.played_losses;
    noContests += record.no_contests;
    for (const game of record.games) {
      if (game.status !== 'played' || game.seed_probability == null) continue;
      const probability = game.seed_probability;
      if (!Number.isFinite(probability) || probability < 0 || probability > 1 || !Number.isInteger(game.seed_trained_through) || game.seed_trained_through >= record.year) {
        throw Error('Earlier scouting probabilities could not be verified.');
      }
      scoredGames++; recordedWins += Number(game.advanced); expectedWins += probability;
    }
  }
  return {window,records,playedGames,noContests,scoredGames,
    recordedWins:scoredGames ? recordedWins : null,
    expectedWins:scoredGames ? expectedWins : null,
    difference:scoredGames ? recordedWins-expectedWins : null};
}

function formMarkup(record) {
  const context=record.form_context;
  if (!context) return '<div class="scout-empty">No published form context for this appearance.</div>';
  const labels={elo:'Within-season Elo',win_rate:'Regular-season win rate',margin:'Mean scoring margin'};
  return `<div class="scout-section-heading"><h3>Pre-March form in this field</h3><p class="note">${context.cutoff_utc ? `${number(context.completed_games,0)} completed games · frozen ${esc(context.cutoff_utc.slice(0,10))}, 00:00 UTC` : 'No verified March 1 form snapshot for this recorded team.'}</p></div>
    <div class="scout-metrics">${Object.entries(labels).map(([kind,label]) => {
      const metric=context.metrics[kind], value=metric.value;
      const display=kind==='win_rate' && value!=null ? `${number(value*100)}%` : number(value);
      return `<article class="scout-metric" data-scout-metric="${kind}"><h4>${label}</h4><strong>${display}</strong><p>${metric.percentile==null ? 'Field percentile —' : `Field percentile ${number(metric.percentile)}`}</p>${metric.percentile==null ? '' : `<div class="scout-percentile" aria-hidden="true"><span style="width:${metric.percentile}%"></span></div>`}<p class="note">${metric.covered_teams} / ${context.field_teams} archived entrants covered${kind==='margin' ? ' · points per game' : ''}</p></article>`;
    }).join('')}</div>
    <p class="note">Percentiles describe covered archived main-bracket entrants, using higher values and half credit for ties. They are not national team rankings. Form freezes before March; this cohort is conditional on preliminary-round survivors. These sources were assembled retrospectively; metric coverage does not establish complete regular-season schedules.</p>`;
}

function historyMarkup(summary, year) {
  const {records,scoredGames,playedGames,noContests}=summary;
  const rowLink=record => `#matchup?${new URLSearchParams({compare_year:record.year,compare_game:record.games[0].id})}`;
  return `<div class="scout-history-summary" role="status">${scoredGames} model-covered games / ${playedGames} played games in ${records.length} earlier recorded appearances · before ${year}. ${noContests} no-contest entries excluded.</div>
    <div class="scout-totals"><div><span>Recorded wins · covered games</span><strong data-scout-total="wins">${number(summary.recordedWins,0)}</strong></div><div><span>Seed expectation · same games</span><strong data-scout-total="expected">${number(summary.expectedWins,2)}</strong></div><div><span>Recorded − expected</span><strong data-scout-total="difference">${signed(summary.difference)}</strong></div></div>
    ${records.length ? `<p class="profile-scroll-hint">Scroll the earlier-results table → for model coverage and expectations.</p><div class="profile-table-scroll" tabindex="0" role="region" aria-label="Earlier tournament scouting evidence, scroll horizontally"><table><caption>Earlier appearances only · expected wins sum saved seed probabilities on the opponents actually faced</caption><thead><tr><th>Year / seed</th><th class="numeric">Covered / played</th><th class="numeric">Wins · covered</th><th class="numeric">Expected</th><th class="numeric">Difference</th></tr></thead><tbody>${records.map(record => {
      const value=record.seed_expectation;
      return `<tr data-scout-year="${record.year}"><th scope="row"><a href="${esc(rowLink(record))}">${record.year} matchups →</a><span class="profile-round">Seed ${record.seed}</span></th><td class="numeric">${value.scored_games} / ${record.played_wins+record.played_losses}</td><td class="numeric">${number(value.recorded_wins,0)}</td><td class="numeric">${number(value.expected_wins,2)}</td><td class="numeric">${signed(value.difference)}</td></tr>`;
    }).join('')}</tbody></table></div>` : '<div class="scout-empty"><h4>No earlier appearances in this identity</h4><p>Earlier archive keys remain separate from verified modern school identities. Cancelled and missing tournaments are not invented.</p></div>'}
    ${records.length && !scoredGames ? '<p class="scout-empty">Played results exist, but this window has no saved earlier-trained seed forecasts. Expectations stay as dashes.</p>' : ''}
    <p class="note scout-boundary">This is a descriptive record on observed tournament paths, not expected full-bracket wins, a player value score or a forecast of future team strength. Tournament outcomes are dependent and rosters change; no confidence interval is estimated. Small samples and missing snapshots limit interpretation. The seed baseline is unchanged and does not consume this dossier.</p>`;
}

export function renderTeamScouting(container, {profile,year,window='5',onWindowChange}) {
  const record=profile.appearances.find(appearance => appearance.year===year);
  if (!record) {
    container.innerHTML=`<div class="scout-empty"><h2>Scouting unavailable for ${year}</h2><p>${profile.coverage.cancelled_years.includes(year) ? 'The tournament was cancelled.' : 'No archived appearance is recorded for this identity in this year; this does not establish qualification.'} Choose a recorded appearance above.</p></div>`;
    return;
  }
  try {
    const summary=scoutingSummary(profile,year,window);
    container.innerHTML=`<header class="scout-heading"><p class="eyebrow">TEAM SCOUTING · HISTORICAL CONTEXT</p><h2>Before the ${year} tournament</h2><p class="note">Retrospective context for a recorded main-bracket participant. The selected tournament's outcomes are excluded from the earlier-results signal; this is not a selection-day full-field forecast.</p></header>${formMarkup(record)}
      <div class="scout-lookback"><div><h3>Earlier results vs seed expectation</h3><p class="note">Choose how many earlier recorded appearances to inspect.</p></div><label for="scout-window">Lookback window<select id="scout-window"><option value="3" ${summary.window==='3'?'selected':''}>Last 3 earlier appearances</option><option value="5" ${summary.window==='5'?'selected':''}>Last 5 earlier appearances</option><option value="all" ${summary.window==='all'?'selected':''}>All earlier appearances in this identity</option></select></label></div><div id="scout-history">${historyMarkup(summary,year)}</div>`;
    const select=container.querySelector('#scout-window');
    select.addEventListener('change',() => {
      const next=scoutingSummary(profile,year,select.value);
      container.querySelector('#scout-history').innerHTML=historyMarkup(next,year);
      onWindowChange?.(next.window);
    });
  } catch(error) {
    container.innerHTML=`<div class="scout-empty" role="alert"><h2>Scouting evidence unavailable</h2><p>${esc(error.message)}</p></div>`;
  }
}
