import {recordStrip} from './track_record.js';
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=value=>value==null?'—':`${(value*100).toFixed(1)}%`;

export async function mountBracketHome(container,{summary,request,bracketMarkup,archiveHref,teamHref,params,isCurrent}){
  const latest=Math.max(...summary.years),hasYear=Number.isFinite(latest);
  container.innerHTML=`<section class="bracket-home"><header class="hero home-hero"><div><p class="eyebrow">MEN’S TOURNAMENT</p><h1>${hasYear?`${latest} bracket`:'Tournament brackets'}</h1><p class="muted">Follow the model’s picks. Open a game. Get to know the teams.</p></div><a class="button" href="#archive" aria-label="Explore the historical bracket">All years →</a></header>${recordStrip(summary.track_record)}<div id="home-bracket" class="loading" role="status" tabindex="-1">Loading the latest historical model bracket…</div><aside class="home-upcoming"><span class="tag">FIELD NOT ANNOUNCED</span><p>2027 team predictions wait for the real field. <a href="#2027">Schedule & field import →</a></p></aside></section>`;
  const target=container.querySelector('#home-bracket');let requestVersion=0;
  const unavailable=message=>`<div class="home-empty"><h2>Model bracket unavailable</h2><p>${esc(message)}</p><a class="button" href="#archive">Browse recorded results</a></div>`;
  if(!hasYear){target.className='';target.innerHTML=unavailable('No completed tournament is bundled. No teams or probabilities have been assumed.');return;}
  const load=async()=>{
    const version=++requestVersion,current=()=>isCurrent()&&version===requestVersion&&target.isConnected;
    const retryFocused=document.activeElement===target.querySelector('#home-retry');
    if(retryFocused)target.focus({preventScroll:true});
    target.className='loading';target.textContent=`Loading ${latest} seed-model picks…`;target.setAttribute('aria-busy','true');
    try{
      const season=await request(`/api/season?year=${latest}`);if(!current())return;
      if(!season.model){target.className='';target.innerHTML=unavailable('No prior-trained model snapshot is available for this tournament. Recorded results remain available.');return;}
      const simulation=await request(`/api/simulate?year=${latest}&rng=2027`);if(!current())return;
      if(!simulation.recommended?.rounds?.length){target.className='';target.innerHTML=unavailable('No saved model-picked path is available. Recorded results remain available.');return;}
      let region=/^[0-4]$/.test(params.get('region')??'')?Number(params.get('region')):0;
      let round=Number(params.get('round'))||1;
      let finderOpen=params.get('teams')==='1',finderQuery=(params.get('find')??'').slice(0,80);
      const field=season.teams.map((team,index)=>({team,index})).sort((a,b)=>a.team.name.localeCompare(b.team.name,'en'));
      const normalize=value=>value.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
      const draw=(focus=null)=>{
        if(!current())return;
        const finals=region===4,first=finals?5:1;
        if(!Number.isInteger(round)||round<first||round>first+(finals?1:3))round=first;
        const groups=simulation.recommended.rounds.map(entry=>{
          const count=entry.games.length/4;
          return {round_name:entry.round_name,games:finals?entry.games:entry.games.slice(region*count,(region+1)*count)};
        }).filter((_,index)=>finals?index>=4:index<4);
        const origin={year:latest,region,view:'recommend',round};
        const finderMarkup=`<details class="home-team-finder" ${finderOpen?'open':''}><summary>Find a team <span>${season.teams.length} in this bracket</span></summary><label for="home-team-search">Team name<input id="home-team-search" type="search" maxlength="80" placeholder="Search this tournament" value="${esc(finderQuery)}" aria-controls="home-team-results" aria-describedby="home-team-note home-team-count"></label><p id="home-team-note" class="note">Open a team’s opening model matchup or recorded history. Title chances use the seed baseline across all possible paths, conditional on the main-bracket field after the First Four.</p><p id="home-team-count" role="status" aria-live="polite"></p><ul id="home-team-results" aria-label="${latest} main-bracket teams"></ul></details>`;
        const leaders=[...simulation.odds].sort((a,b)=>b.champion-a.champion).slice(0,4);
        target.className='home-loaded';target.removeAttribute('role');
        target.innerHTML=`<p class="home-context"><strong>SEED-MODEL PICKS</strong><span>Historical ${latest} · 64 teams after First Four · trained through ${simulation.recommended.trained_through}</span></p>${finderMarkup}<div class="home-layout"><section class="home-path" aria-label="Historical model-picked bracket"><div class="segmented home-regions" role="group" aria-label="Home bracket region">${[0,1,2,3,4].map(index=>`<button data-home-region="${index}" aria-pressed="${index===region}">${index===4?'Final Four':`Region ${index+1}`}</button>`).join('')}</div><p class="home-key">✓ Model pick · blue % is the top team’s seed chance.</p><label class="mobile-round" for="home-round">Round<select id="home-round">${groups.map((entry,index)=>`<option value="${index+first}" ${round===index+first?'selected':''}>${esc(entry.round_name)}</option>`).join('')}</select></label>${bracketMarkup(groups,finals?2:8,season.teams,round-first)}<a class="home-all" href="${archiveHref(origin)}">Open full model bracket →</a></section><aside class="home-chances"><p class="eyebrow">ACROSS ALL POSSIBLE PATHS</p><h2>Title chances</h2><p class="note">Conditional on the 64 main-bracket teams after the First Four.</p><ol>${leaders.map(team=>{
          const record=season.teams.find(entry=>entry.id===team.team),from={...origin,region:Math.max(0,Math.floor(season.teams.findIndex(entry=>entry.id===team.team)/16)),round:1};
          return `<li>${record?.profile_id?`<a href="${teamHref(record.profile_id,from)}">${esc(team.name)}</a>`:`<span>${esc(team.name)}</span>`}<strong>${pct(team.champion)}</strong></li>`;
        }).join('')}</ol><a href="#evidence?year=${latest}">Model record & sources →</a></aside></div><details class="home-method"><summary>How these picks work & where they stop</summary><p>${esc(simulation.recommended.method)} This is a historical experiment, not a live or 2027 forecast. First Four games/losers are missing; it is not a selection-day full-field forecast.</p><p class="note">Seeds only: no roster updates, injuries, market prices or current-form statistics. Later opponents follow model picks, not recorded winners. Region numbers preserve the source order; geographic names are unavailable. Title chances integrate every possible path, not the chance all the picks are correct.</p><a href="#about">Data coverage & provenance →</a></details>`;
        target.querySelectorAll('[data-game]').forEach(card=>{
          const link=document.createElement('a');link.className=card.className;link.style.cssText=card.style.cssText;link.innerHTML=card.innerHTML;link.dataset.homeGame=card.dataset.game;
          const [column]=card.dataset.game.split('-').map(Number);
          link.href=archiveHref({...origin,game:card.dataset.game,round:column+first})+'&open=1';link.setAttribute('aria-label',card.getAttribute('aria-label'));card.replaceWith(link);
        });
        const sync=()=>{
          const query=new URLSearchParams({region,round});
          if(finderOpen)query.set('teams','1');
          if(finderQuery)query.set('find',finderQuery);
          history.replaceState(history.state,'',`#home?${query}`);
        };
        const finder=target.querySelector('.home-team-finder'),input=target.querySelector('#home-team-search');
        const filterTeams=()=>{
          const needle=normalize(finderQuery),matches=finderQuery.trim()?field.filter(({team})=>needle&&normalize(team.name).includes(needle)):field;
          target.querySelector('#home-team-count').textContent=`${matches.length} of ${field.length} teams${finderQuery.trim()?' match':''}.`;
          target.querySelector('#home-team-results').innerHTML=matches.length?matches.map(({team,index})=>{
            const from={year:latest,region:Math.floor(index/16),round:1,view:'recommend',game:`0-${Math.floor(index%16/2)}`};
            const chance=simulation.odds.find(entry=>entry.team===team.id)?.champion;
            return `<li data-home-team="${esc(team.id)}"><a class="home-team-matchup" data-home-team-link="${esc(team.id)}:matchup" href="${archiveHref(from)}&open=1" aria-label="${esc(team.name)} opening model matchup"><strong>${esc(team.name)}</strong><span>Seed ${esc(team.seed)} · Region ${from.region+1} · Title ${pct(chance)}</span><span>Opening matchup →</span></a>${team.profile_id?`<a class="home-team-history" data-home-team-link="${esc(team.id)}:history" href="${teamHref(team.profile_id,from)}" aria-label="${esc(team.name)} tournament history">Team history →</a>`:'<span class="note">History unavailable</span>'}</li>`;
          }).join(''):'<li class="home-team-empty">No teams match. Try another name.</li>';
        };
        filterTeams();
        input.oninput=()=>{if(current()&&input.isConnected){finderQuery=input.value.slice(0,80);filterTeams();sync();}};
        finder.ontoggle=()=>{if(current()&&finder.isConnected&&finder.open!==finderOpen){finderOpen=finder.open;sync();}};
        target.onclick=event=>{
          const link=event.target.closest?.('[data-home-team-link]');
          if(!current()||!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
          const state=history.state&&typeof history.state==='object'?history.state:{};
          history.replaceState({...state,marchHomeReturn:{route:location.hash,key:link.dataset.homeTeamLink}},'',location.href);
        };
        target.querySelectorAll('[data-home-region]').forEach(button=>button.onclick=()=>{region=Number(button.dataset.homeRegion);round=region===4?5:1;sync();draw(`[data-home-region="${region}"]`);});
        target.querySelector('#home-round').onchange=event=>{round=Number(event.target.value);sync();draw('#home-round');};
        if(focus)target.querySelector(focus)?.focus({preventScroll:true});
        else if(history.state?.marchHomeReturn?.route===location.hash){
          const link=[...target.querySelectorAll('[data-home-team-link]')].find(link=>link.dataset.homeTeamLink===history.state.marchHomeReturn.key);
          link?.focus();
        }
      };
      draw();if(retryFocused)target.querySelector('[data-home-region]')?.focus({preventScroll:true});
    }catch(error){if(current()){
      target.className='home-empty';target.innerHTML=`<h2>Bracket couldn’t load</h2><p role="alert">${esc(error.message)}</p><button id="home-retry" class="primary">Try bracket again</button> <a href="#archive">Browse recorded results</a>`;
      target.querySelector('#home-retry').onclick=load;if(retryFocused)target.querySelector('#home-retry').focus({preventScroll:true});
    }}finally{if(current())target.removeAttribute('aria-busy');}
  };
  await load();
}
