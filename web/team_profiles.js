import {renderTeamScouting} from './team_scouting.js';
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const count=value=>Number(value).toLocaleString('en-US');

export function archiveHref(origin){
  const query=new URLSearchParams({year:origin.year,region:origin.region??0,view:origin.view==='sample'?'sample':'actual'});
  if(origin.game)query.set('game',origin.game);
  return `#archive?${query}`;
}

export function teamHref(profileId,origin,appearance=origin.year){
  const query=new URLSearchParams({profile:profileId,from:origin.year,from_region:origin.region??0,appearance});
  if(origin.game)query.set('from_game',origin.game);
  if(origin.view==='sample')query.set('from_view','sample');
  return `#team?${query}`;
}

function appearanceMarkup(record,profile,origin){
  if(!record)return '';
  const last=record.games.at(-1);
  const bracket=archiveHref({year:record.year,region:last.round>=5?4:record.region,game:last.id});
  const played=record.played_wins+record.played_losses;
  return `<div class="profile-section-heading"><div><p class="eyebrow">RECORDED APPEARANCE</p><h2>${record.year} · seed ${record.seed}</h2></div><a class="button profile-secondary" href="${bracket}">Open ${record.year} bracket →</a></div>
    <p class="profile-record-label">Recorded name: <strong>${esc(record.name)}</strong> · archive key <code>${esc(record.archive_id)}</code></p>
    <div class="profile-coverage"><span>Final stage <strong>${esc(record.final_stage)}</strong></span><span>Scores & dates <strong>${record.scores_and_dates} / ${played} played games</strong></span><span>Pre-March form <strong>${record.form_available?'Available':'— · not bundled'}</strong></span></div>
    ${record.no_contests?'<p class="profile-callout">No-contest outcomes are listed separately from played wins and losses.</p>':''}
    <p class="profile-scroll-hint">Scroll the results table → for scores and dates.</p><div class="profile-table-scroll" tabindex="0" role="region" aria-label="Recorded tournament games, scroll horizontally for scores"><table><caption>${record.year} main-bracket results · missing scores and dates stay as dashes</caption><thead><tr><th>Round & opponent</th><th>Result</th><th>Score</th><th>Date · UTC</th></tr></thead><tbody>${record.games.map(game=>`<tr><th scope="row"><span class="profile-round">${esc(game.round_name)}</span><a href="${teamHref(game.opponent_profile_id,origin,record.year)}">${esc(game.opponent_name)}</a></th><td>${esc(game.result)}</td><td class="numeric">${game.score_for==null||game.score_against==null?'—':`${game.score_for}–${game.score_against}`}</td><td>${game.date_utc?esc(game.date_utc.slice(0,10)):'—'}</td></tr>`).join('')}</tbody></table></div>`;
}

export async function renderTeamProfile(container,{profileId,request,origin,appearanceYear,scoutWindow='5',isCurrent=()=>true}){
  const back=archiveHref(origin);
  const shell=(body)=>`<section class="team-profile"><a class="profile-back" href="${back}">← Back to ${origin.year} bracket</a>${body}</section>`;
  container.innerHTML=shell('<p class="eyebrow">MARCH LAB · TEAM HISTORY</p><h1>Team history</h1><div class="profile-empty" role="status">Loading recorded tournament appearances and scouting evidence…</div>');
  try{
    const profile=await request(`/api/team?profile=${encodeURIComponent(profileId)}`);
    if(!isCurrent())return;
    const records=profile.appearances,totals=profile.totals,modern=profile.identity_kind==='verified_schedule_id';
    const first=Math.min(...records.map(r=>r.year)),last=Math.max(...records.map(r=>r.year));
    const initial=Number.isInteger(appearanceYear)?appearanceYear:records[0].year;
    document.title=`${profile.name} · Team history · March Lab`;
    container.innerHTML=shell(`<header class="profile-hero"><div class="profile-letter" aria-hidden="true">${esc(profile.name.slice(0,1))}</div><div><p class="eyebrow">MARCH LAB · TEAM HISTORY</p><h1>${esc(profile.name)}</h1><p>${modern?'Verified modern source identity':'Exact archive-key history'} · ${first}–${last} recorded appearances</p></div></header>
      <p class="profile-callout"><strong>${modern?'Verified schedule ID':'Archive key'}: ${esc(profile.source_id)}</strong>${esc(profile.coverage.identity_note)} Tournament history only; rosters and player statistics are not bundled.</p>
      <div class="profile-stats"><div><strong>${count(totals.appearances)}</strong><span>Recorded appearances</span></div><div><strong>${count(totals.played_wins)}–${count(totals.played_losses)}</strong><span>Played main-bracket wins–losses</span></div><div><strong>${count(totals.titles)}</strong><span>Titles in this coverage</span></div></div>
      <p class="note">${totals.no_contests?`${count(totals.no_contests)} no-contest entries · ${count(totals.no_contest_advancements)} no-contest advancements. `:''}These are covered records, not a complete school career or a forecast.</p>
      <div class="profile-selector"><label for="profile-year">Explore a recorded tournament<select id="profile-year">${!records.some(r=>r.year===initial)?`<option value="${initial}">${initial} · no recorded appearance</option>`:''}${records.map(record=>`<option value="${record.year}" ${record.year===initial?'selected':''}>${record.year} · seed ${record.seed} · ${esc(record.final_stage)}</option>`).join('')}</select></label></div>
      <div id="profile-status" class="statusline" role="status" aria-live="polite"></div><section id="team-scouting" class="team-scouting" aria-label="Historical team scouting dossier"></section><section id="profile-appearance"></section>
      <details class="profile-history"><summary>All ${records.length} recorded appearances</summary><div class="profile-table-scroll" tabindex="0" role="region" aria-label="All recorded appearances, scroll horizontally for results"><table><caption>Appearances within this identity and coverage only</caption><thead><tr><th>Year</th><th>Recorded name</th><th>Seed</th><th>Final stage</th><th>Played W–L</th></tr></thead><tbody>${records.map(record=>`<tr><td><button data-appearance="${record.year}" aria-label="View ${record.year} appearance">${record.year}</button></td><td>${esc(record.name)}</td><td>${record.seed}</td><td>${esc(record.final_stage)}</td><td>${record.played_wins}–${record.played_losses}</td></tr>`).join('')}</tbody></table></div></details>
      ${profile.separate_records.length?`<details><summary>Overlapping archive labels · separate identities</summary><p class="note">A shared archive label does not verify the same school. These records are kept separate and are excluded from the totals above.</p><div class="profile-related">${profile.separate_records.map(other=>`<a href="${teamHref(other.id,origin,other.last_year)}">${esc(other.name)}<span>${other.identity_kind==='archive_key'?'Uncrosswalked archive key':'Separate verified source ID'} · ${other.first_year}–${other.last_year}</span></a>`).join('')}</div></details>`:''}
      <section class="profile-boundary"><h2>Where this history ends</h2><p>${esc(profile.coverage.scope)} ${esc(profile.coverage.identity_note)}</p><p>${profile.coverage.cancelled_years.map(esc).join(', ')} was cancelled and is not an appearance for any team. Other absent years do not establish qualification history. ${profile.coverage.missing_years.length?`${Math.min(...profile.coverage.missing_years)}–${Math.max(...profile.coverage.missing_years)} is missing from the bundled archive.`:''} Names and results come from the existing <a href="${esc(profile.coverage.source)}">historical archive</a>; modern crosswalks and score enrichment come from the published SportsDataverse/ESPN artifacts.</p></section>`);
    const select=container.querySelector('#profile-year'),detail=container.querySelector('#profile-appearance'),status=container.querySelector('#profile-status');
    let lookback=['3','5','all'].includes(String(scoutWindow))?String(scoutWindow):'5';
    const show=(year,updateUrl=false)=>{
      const record=records.find(r=>r.year===year);
      detail.innerHTML=record?appearanceMarkup(record,profile,origin):`<div class="profile-empty"><h2>No recorded appearance for ${year}</h2><p>${profile.coverage.cancelled_years.includes(year)?'The tournament was cancelled.':'This profile has no recorded appearance for this year; that does not establish the team’s qualification history.'} Choose an available tournament above.</p></div>`;
      status.textContent=record?`${year} recorded results loaded.`:`No recorded appearance for ${year}.`;
      renderTeamScouting(container.querySelector('#team-scouting'),{profile,year,window:lookback,onWindowChange:window=>{lookback=window;const url=new URL(location.href),query=new URLSearchParams(url.hash.split('?')[1]);query.set('scout_window',window);url.hash=`team?${query}`;history.replaceState(null,'',url);}});
      if(updateUrl){const url=new URL(location.href),query=new URLSearchParams(url.hash.split('?')[1]);query.set('appearance',year);url.hash=`team?${query}`;history.replaceState(null,'',url);}
    };
    select.value=String(initial);show(initial);
    select.addEventListener('change',()=>show(Number(select.value),true));
    container.querySelectorAll('[data-appearance]').forEach(button=>button.addEventListener('click',()=>{select.value=button.dataset.appearance;show(Number(select.value),true);detail.scrollIntoView({block:'start'});}));
  }catch(error){
    if(!isCurrent())return;
    container.innerHTML=shell(`<p class="eyebrow">MARCH LAB · TEAM HISTORY</p><h1>Team history unavailable</h1><div class="profile-empty" role="alert"><p>${esc(error.message)}</p><p>Tournament totals are unavailable for this profile. Return to the bracket or try loading its recorded history again.</p><button id="profile-retry">Retry team history</button></div>`);
    container.querySelector('#profile-retry').addEventListener('click',()=>renderTeamProfile(container,{profileId,request,origin,appearanceYear,scoutWindow,isCurrent}));
  }
}
