"""Real browser smoke test (Edge or Chromium): python tests/browser_check.py."""
from pathlib import Path
import json
import hashlib
import os
import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect
from scouting_browser import assert_team_scouting
from theme_browser import assert_theme_journeys
from bracket_drilldown_browser import assert_bracket_drilldowns

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8037'
STATIC='--static' in sys.argv


def assert_skip_preserves_archive(page):
    route = page.url
    content = page.locator('main').inner_html()
    selected_year = page.locator('#archive-year').input_value()
    page.get_by_role('link', name='Skip to content', exact=True).focus()
    page.keyboard.press('Enter')
    expect(page.locator('main')).to_be_focused()
    expect(page).to_have_url(route)
    expect(page.locator('nav a[href="#archive"]')).to_have_attribute('aria-current', 'page')
    assert page.locator('main').inner_html() == content
    expect(page.locator('#archive-year')).to_have_value(selected_year)


def capture_insight_state(page, shots, state):
    previous=page.viewport_size
    panel=page.locator('#season-insights')
    for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        panel.screenshot(path=str(shots/f'season-evidence-{state}-{name}.png'))
    page.set_viewport_size(previous)


def assert_season_evidence(page, shots):
    panel=page.locator('#season-insights')
    expect(panel.get_by_role('heading',name='Season evidence',exact=True)).to_be_visible()
    expect(page.locator('#insight-status')).to_have_text('1985 evidence loaded.')
    expect(panel).to_contain_text('Warm-up · unscored')
    expect(panel).to_contain_text('— · no prediction snapshot')
    # Feature coverage must not be presented as model availability.
    page.select_option('#insight-year','2006')
    expect(page.locator('#insight-status')).to_have_text('2006 evidence loaded.')
    expect(panel).to_contain_text('64 / 64 teams')
    expect(panel).to_contain_text('too few earlier feature-covered games')
    expect(panel.locator('tbody tr').last).to_contain_text('—')
    page.select_option('#insight-year','2008')
    expect(page.locator('#insight-status')).to_have_text('2008 evidence loaded.')
    expect(panel).to_contain_text('form challenger has an earlier training snapshot')
    expect(panel.locator('tbody tr').last).not_to_contain_text('—')
    page.select_option('#insight-year','2021')
    expect(page.locator('#insight-status')).to_have_text('2021 evidence loaded.')
    expect(panel).to_contain_text('62 played games')
    expect(panel).to_contain_text('1 no-contest advancement excluded')
    # Cancelled tournaments have no fabricated coverage, scores or bracket link.
    page.select_option('#insight-year','2020')
    expect(panel).to_contain_text('TOURNAMENT CANCELLED')
    expect(panel.locator('#insight-archive')).to_have_count(0)
    capture_insight_state(page,shots,'cancelled')
    page.select_option('#insight-year','1995')
    expect(page.locator('#insight-status')).to_have_text('1995 evidence loaded.')
    expect(panel).to_contain_text('0 / 63')
    expect(panel).to_contain_text('0 / 64 teams')
    expect(panel).to_contain_text('No prior calibration fit · temperature 1')
    page.select_option('#insight-year','2026')
    expect(page.locator('#insight-status')).to_have_text('2026 evidence loaded.')
    expect(panel).to_contain_text('2,519 earlier games · through 2025')
    expect(panel).to_contain_text('1,889 earlier predictions · through 2025')
    expect(panel.locator('tbody tr').nth(2)).to_contain_text('0.16585')
    panel.get_by_text('How to read this evidence',exact=True).click()
    expect(panel).to_contain_text('not a guarantee of future accuracy')
    panel.screenshot(path=str(shots/'season-evidence-desktop.png'))
    page.set_viewport_size({'width':390,'height':844})
    panel.scroll_into_view_if_needed()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    expect(panel.get_by_text('On narrow screens, scroll the table → to compare scores.',exact=True)).to_be_visible()
    comparison=panel.get_by_role('region',name='Saved tournament evaluation, scroll horizontally to compare scores')
    page.set_viewport_size({'width':320,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    comparison.focus();page.keyboard.press('ArrowRight')
    page.wait_for_function('document.querySelector("#season-insights .table-scroll").scrollLeft > 0')
    page.set_viewport_size({'width':390,'height':844})
    comparison.evaluate('(element)=>element.scrollLeft=0')
    panel.screenshot(path=str(shots/'season-evidence-mobile.png'))
    # The archive action opens the inspected season, including with keyboard input.
    page.select_option('#insight-year','2006')
    expect(page.locator('#insight-status')).to_have_text('2006 evidence loaded.')
    page.locator('#insight-archive').focus();page.keyboard.press('Enter')
    expect(page.locator('#archive-year')).to_have_value('2006')
    expect(page.locator('.game')).to_have_count(15)
    # Back/forward must return to the evidence route and the inspected bracket.
    page.go_back()
    expect(page.locator('nav a[href="#evidence"]')).to_have_attribute('aria-current','page')
    expect(page.locator('#insight-year')).to_have_value('2006')
    expect(page.locator('#insight-status')).to_have_text('2006 evidence loaded.')
    page.go_forward()
    expect(page.locator('nav a[href="#archive"]')).to_have_attribute('aria-current','page')
    expect(page.locator('#archive-year')).to_have_value('2006')
    page.set_viewport_size({'width':1440,'height':1000})


def assert_insight_request_states(page, shots):
    # A late response must not replace the newer selected year.
    page.goto(BASE+'/#evidence')
    page.reload()
    expect(page.locator('#insight-status')).to_have_text('2026 evidence loaded.')
    path='**/data/seasons/2006.json' if STATIC else '**/api/season?year=2006'
    pending=[]
    page.route(path,lambda route:pending.append(route))
    page.select_option('#insight-year','2006')
    expect(page.locator('#insight-status')).to_have_text('Loading 2006 evidence…')
    expect(page.locator('#insight-content')).to_have_attribute('aria-busy','true')
    expect(page.locator('#insight-content table')).to_have_count(0)
    capture_insight_state(page,shots,'loading')
    page.select_option('#insight-year','1985')
    expect(page.locator('#insight-status')).to_have_text('1985 evidence loaded.')
    assert len(pending)==1
    with page.expect_response(lambda response:'2006' in response.url):
        pending[0].continue_()
    page.wait_for_load_state('networkidle')
    expect(page.locator('#insight-content h3').first).to_have_text('1985 tournament')
    expect(page.locator('#insight-year')).to_have_value('1985')
    page.unroute(path)
    # Errors leave a working selector and an explicit retry; no stale scores.
    path='**/data/seasons/1996.json' if STATIC else '**/api/season?year=1996'
    page.route(path,lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Evidence temporarily unavailable"}'))
    page.select_option('#insight-year','1996')
    expect(page.locator('#insight-status')).to_contain_text('Could not load 1996 evidence:')
    if STATIC:
        expect(page.locator('#insight-status')).to_contain_text('The saved snapshot could not be loaded. Try again.')
        expect(page.locator('#insight-status')).not_to_contain_text('no published snapshot')
    expect(page.locator('#insight-content table')).to_have_count(0)
    expect(page.get_by_role('heading',name='Evidence unavailable',exact=True)).to_be_visible()
    capture_insight_state(page,shots,'error')
    page.unroute(path)
    page.get_by_role('button',name='Retry season evidence',exact=True).focus();page.keyboard.press('Enter')
    expect(page.locator('#insight-status')).to_have_text('1996 evidence loaded.')
    expect(page.locator('#insight-content h3').first).to_have_text('1996 tournament')
    # Interactions remain stable and use no transitions with reduced motion.
    page.emulate_media(reduced_motion='reduce')
    page.locator('#insight-year').focus()
    assert page.locator('#insight-year').evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s'
    page.select_option('#insight-year','2020')
    expect(page.locator('#insight-content')).to_contain_text('TOURNAMENT CANCELLED')
    page.emulate_media(reduced_motion='no-preference')


def assert_profile_navigation_regressions(page):
    # Fixed browser clock controls the seeded draw; all teams/results stay bundled data.
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(BASE+'/#archive?year=2026&region=0');page.reload()
    expect(page.locator('.game')).to_have_count(15)
    page.evaluate('Date.now=()=>42')
    page.locator('#draw-bracket').click()
    expect(page.locator('[data-view="sample"]')).to_have_attribute('aria-pressed','true')
    original_draw=page.locator('.bracket').inner_html()
    page.locator('.game').first.click();page.locator('#detail-title a').first.click()
    expect(page.locator('#profile-year')).to_be_visible()
    # Same-year recorded-appearance links must show historical results even with a saved draw.
    page.get_by_role('link',name='Open 2026 bracket →').click()
    expect(page.locator('[data-view="actual"]')).to_have_attribute('aria-pressed','true')
    expect(page.locator('.bracket-key')).to_contain_text('Actual winner')
    expect(page.locator('#season-content')).to_contain_text('The bracket above shows recorded actual results.')
    expect(page.locator('#season-content')).not_to_contain_text('The draw above is one sample.')
    assert 'view=actual' in page.url
    expect(page.locator('.game:focus')).to_contain_text('Duke')
    # Browsing another tournament must preserve the original in-session 2026 draw.
    page.go_back();expect(page.locator('#profile-year')).to_have_value('2026')
    page.select_option('#profile-year','2015')
    page.get_by_role('link',name='Open 2015 bracket →').click()
    expect(page.locator('#archive-year')).to_have_value('2015')
    expect(page.locator('.bracket-key')).to_contain_text('Actual winner')
    page.go_back();expect(page.locator('#profile-year')).to_have_value('2015')
    page.go_back();expect(page.locator('#archive-year')).to_have_value('2026')
    expect(page.locator('[data-view="sample"]')).to_have_attribute('aria-pressed','true')
    assert 'view=sample' in page.url
    assert page.locator('.bracket').inner_html()==original_draw
    # Reload cannot recover an ephemeral draw: both the URL and label become actual.
    page.reload()
    expect(page.locator('.bracket-key')).to_contain_text('Actual winner')
    expect(page.locator('[data-view="sample"]')).to_have_count(0)
    assert 'view=actual' in page.url
    for width in (1440,390):
        page.set_viewport_size({'width':width,'height':1000 if width==1440 else 844})
        page.goto(BASE+'/#archive?year=2026&region=0');page.reload()
        expect(page.locator('.game')).to_have_count(15)
        page.select_option('#archive-year','2021')
        expect(page.locator('.stat').nth(1)).to_contain_text('62')
        page.locator('[data-region="2"]').click()
        original_bracket=page.locator('.bracket').inner_html()
        card=page.get_by_role('button',name='Oregon versus VCU, Round of 64, open details')
        card.focus();page.keyboard.press('Enter')
        page.locator('dialog').get_by_role('link',name='Oregon',exact=True).click()
        expect(page.locator('#profile-year')).to_have_value('2021')
        page.go_back()
        expect(page.locator('#archive-year')).to_have_value('2021')
        expect(page.locator('[data-region="2"]')).to_have_attribute('aria-pressed','true')
        expect(card).to_be_focused()
        assert all(value in page.url for value in ('year=2021','region=2','view=actual'))
        assert page.locator('.bracket').inner_html()==original_bracket
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.go_forward();expect(page.locator('#profile-year')).to_have_value('2021')
    # Delayed successful and failed draws must leave the profile and return view intact.
    page.set_viewport_size({'width':1440,'height':1000})
    path='**/data/tables/2026.json' if STATIC else '**/api/simulate?*'
    for outcome in ('success','failure'):
        page.goto(BASE+'/#archive?year=2026&region=0');page.reload()
        expect(page.locator('.game')).to_have_count(15)
        page.evaluate('Date.now=()=>42')
        pending=[]
        page.route(path,lambda route:pending.append(route))
        page.locator('#draw-bracket').click()
        expect(page.locator('#draw-bracket')).to_have_text('Calculating…')
        page.locator('.game').first.click();page.locator('#detail-title a').first.click()
        expect(page.locator('#profile-year')).to_be_visible()
        original_profile=page.locator('main').inner_html()
        assert len(pending)==1
        if outcome=='success':
            pending[0].continue_()
        else:
            pending[0].fulfill(status=503,content_type='application/json',body='{"error":"Controlled simulation failure"}')
        page.wait_for_load_state('networkidle')
        assert page.locator('main').inner_html()==original_profile
        expect(page.get_by_role('heading',name='Duke',exact=True)).to_be_visible()
        page.unroute(path)
        page.get_by_role('link',name='← Back to 2026 bracket').click()
        expect(page.locator('.bracket-key')).to_contain_text('Actual winner')
        expect(page.locator('[data-view="sample"]')).to_have_count(0)
        expect(page.locator('#draw-bracket')).to_be_enabled()
        assert 'view=actual' in page.url


def assert_team_profiles(page, shots):
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(BASE+'/#archive?year=2026&region=0')
    card=page.get_by_role('button',name='Duke versus Siena, Round of 64, open details')
    card.focus();page.keyboard.press('Enter')
    link=page.locator('dialog').get_by_role('link',name='Duke',exact=True)
    link.focus();page.keyboard.press('Enter')
    profile=page.locator('.team-profile')
    expect(profile.get_by_role('heading',name='Duke',exact=True)).to_be_visible()
    expect(page.locator('dialog')).not_to_be_visible()
    expect(profile.locator('.profile-stats')).to_contain_text('19')
    expect(profile.locator('.profile-stats')).to_contain_text('46–17')
    expect(profile).to_contain_text('not a complete school career')
    expect(profile).to_contain_text('rosters and player statistics are not bundled')
    page.select_option('#profile-year','2015')
    expect(profile.get_by_role('heading',name='2015 · seed 1')).to_be_visible()
    expect(page.locator('#profile-appearance')).to_contain_text('Champion')
    assert 'appearance=2015' in page.url
    # Browsing older results must preserve the origin bracket, game and focus.
    profile.get_by_role('link',name='← Back to 2026 bracket').focus();page.keyboard.press('Enter')
    expect(page.locator('#archive-year')).to_have_value('2026')
    expect(card).to_be_focused()
    expect(page.locator('[data-region="0"]')).to_have_attribute('aria-pressed','true')
    page.go_back();expect(page.locator('#profile-year')).to_have_value('2015')
    page.go_forward();expect(card).to_be_focused()
    page.get_by_role('button',name='Simulate this field',exact=True).click()
    expect(page.get_by_role('heading',name='Advancement probabilities · 2026')).to_be_visible(timeout=15000)
    sample_cards=page.locator('.bracket').inner_html()
    page.locator('.game').first.click()
    page.locator('#detail-title a').first.click()
    expect(page.locator('#profile-year')).to_be_visible()
    profile.get_by_role('link',name='← Back to 2026 bracket').click()
    expect(page.locator('[data-view="sample"]')).to_have_attribute('aria-pressed','true')
    assert page.locator('.bracket').inner_html()==sample_cards
    # A direct selected-appearance link opens the matching year/region/round.
    page.go_back()
    page.select_option('#profile-year','2015')
    page.locator('#profile-appearance').get_by_role('link',name='Open 2015 bracket →').click()
    expect(page.locator('#archive-year')).to_have_value('2015')
    expect(page.locator('[data-region="4"]')).to_have_attribute('aria-pressed','true')
    expect(page.locator('.game:focus')).to_contain_text('Duke')
    # No guessed join of old labels or of labels reused by different schools.
    page.goto(BASE+'/#team?profile=archive%3ADuke&from=2026&appearance=2005')
    expect(profile).to_contain_text('Exact archive-key history')
    expect(profile.locator('.profile-stats')).to_contain_text('20')
    expect(page.locator('#profile-appearance')).to_contain_text('0 / 3 played games')
    expect(page.locator('#profile-appearance tbody td').last).to_have_text('—')
    profile.get_by_text('Overlapping archive labels · separate identities',exact=True).click()
    profile.locator('.profile-related a').filter(has_text='Duke').click()
    expect(profile).to_contain_text('Verified schedule ID: 150')
    page.goto(BASE+'/#team?profile=espn%3A301&from=2008&appearance=2008')
    expect(profile.get_by_role('heading',name='San Diego',exact=True)).to_be_visible()
    expect(profile.locator('.profile-stats strong').first).to_have_text('1')
    profile.get_by_text('Overlapping archive labels · separate identities',exact=True).click()
    profile.locator('.profile-related a').filter(has_text='UC San Diego').click()
    expect(profile.get_by_role('heading',name='UC San Diego',exact=True)).to_be_visible()
    expect(profile.locator('.profile-stats strong').first).to_have_text('1')
    # No-contest is separate even for the team that did not advance.
    page.goto(BASE+'/#team?profile=espn%3A2483&from=2021&from_region=2&appearance=2021')
    expect(page.locator('#profile-appearance')).to_contain_text('No contest · advanced')
    expect(page.locator('#profile-appearance')).to_contain_text('2 / 2 played games')
    page.locator('#profile-appearance').get_by_role('link',name='VCU',exact=True).click()
    expect(page.locator('#profile-appearance')).to_contain_text('No contest · did not advance')
    expect(page.locator('#profile-appearance')).to_contain_text('0 / 0 played games')
    expect(page.locator('#profile-appearance tbody td').nth(1)).to_have_text('—')
    page.screenshot(path=str(shots/'team-profile-no-contest-desktop.png'),full_page=True)
    # Cancelled and other absent years show an empty appearance, not zero career data.
    page.goto(BASE+'/#team?profile=espn%3A150&from=2026&appearance=2020')
    expect(profile.get_by_role('heading',name='No recorded appearance for 2020')).to_be_visible()
    expect(page.locator('#profile-appearance')).to_contain_text('The tournament was cancelled.')
    expect(page.locator('#profile-appearance table')).to_have_count(0)
    page.screenshot(path=str(shots/'team-profile-cancelled-desktop.png'),full_page=True)
    page.goto(BASE+'/#team?profile=espn%3A150&from=2026&appearance=2021')
    expect(page.locator('#profile-appearance')).to_contain_text('does not establish the team’s qualification history')
    page.select_option('#profile-year','2026')
    # Responsive typography, controls, table scrolling and reduced motion.
    page.locator('#profile-year').focus()
    page.screenshot(path=str(shots/'team-profile-desktop.png'),full_page=True)
    for width in (768,390,320):
        page.set_viewport_size({'width':width,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    results=profile.get_by_role('region',name='Recorded tournament games, scroll horizontally for scores')
    results.focus();page.keyboard.press('ArrowRight')
    page.wait_for_function('document.querySelector("#profile-appearance .profile-table-scroll").scrollLeft > 0')
    page.set_viewport_size({'width':390,'height':844})
    results.evaluate('(e)=>e.scrollLeft=0')
    page.locator('#profile-year').focus()
    page.screenshot(path=str(shots/'team-profile-mobile.png'),full_page=True)
    profile.get_by_text('All 19 recorded appearances',exact=True).click()
    history_table=profile.get_by_role('region',name='All recorded appearances, scroll horizontally for results')
    history_table.focus();page.keyboard.press('ArrowRight')
    page.wait_for_function('document.querySelector(".profile-history .profile-table-scroll").scrollLeft > 0')
    profile.get_by_role('button',name='View 2010 appearance').click()
    expect(page.locator('#profile-year')).to_have_value('2010')
    page.emulate_media(reduced_motion='reduce')
    assert page.locator('#profile-year').evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s'
    page.emulate_media(reduced_motion='no-preference')
    # Return focus restores the matching mobile round, even for a later round.
    profile.get_by_role('link',name='← Back to 2026 bracket').click()
    expect(page.locator('#archive-year')).to_have_value('2026')
    page.select_option('#mobile-round','2')
    card=page.locator('.game:visible').first
    card.focus();page.keyboard.press('Enter')
    page.locator('#detail-title a').first.focus();page.keyboard.press('Enter')
    expect(page.locator('#profile-year')).to_be_visible()
    profile.get_by_role('link',name='← Back to 2026 bracket').click()
    expect(page.locator('#mobile-round')).to_have_value('2')
    expect(page.locator('.game:focus')).to_be_visible()
    # A missing ID is an explicit unavailable view, never a guessed school.
    page.goto(BASE+'/#team?profile=missing&from=2026')
    expect(profile.get_by_role('heading',name='Team history unavailable')).to_be_visible()
    expect(profile).to_contain_text('exact profile ID')
    expect(profile.locator('.profile-stats')).to_have_count(0)
    page.screenshot(path=str(shots/'team-profile-unavailable-mobile.png'),full_page=True)
    if not STATIC:
        assert page.request.get(BASE+'/api/team?profile=missing').status==404
    # A failed fetch can be retried with Enter; late responses cannot replace a new route.
    page.set_viewport_size({'width':1440,'height':1000})
    path='**/data/teams/*.json' if STATIC else '**/api/team?profile=*'
    page.route(path,lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Team history temporarily unavailable"}'))
    page.goto(BASE+'/#team?profile=espn%3A150&from=2026&appearance=2026')
    page.reload()
    expect(profile.get_by_role('heading',name='Team history unavailable')).to_be_visible()
    page.unroute(path)
    profile.get_by_role('button',name='Retry team history',exact=True).focus();page.keyboard.press('Enter')
    expect(profile.get_by_role('heading',name='Duke',exact=True)).to_be_visible()
    pending=[]
    path='**/data/teams/'+hashlib.sha256(b'espn:150').hexdigest()+'.json' if STATIC else '**/api/team?profile=*'
    page.route(path,lambda route:pending.append(route))
    # Reload clears static request caches before testing the delayed request.
    page.reload()
    expect(profile.get_by_role('status')).to_contain_text('Loading recorded tournament appearances')
    page.locator('nav').get_by_role('link',name='Matchup lab').click()
    expect(page.get_by_role('heading',name='Matchup lab',exact=True)).to_be_visible()
    assert len(pending)==1
    for route in pending:
        route.continue_()
    page.wait_for_load_state('networkidle')
    expect(page.get_by_role('heading',name='Matchup lab',exact=True)).to_be_visible()
    expect(profile).to_have_count(0)
    page.unroute(path)


def capture_comparison(page,shots,state):
    previous=page.viewport_size
    panel=page.locator('#matchup-comparison')
    for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        panel.screenshot(path=str(shots/f'matchup-comparison-{state}-{name}.png'))
    page.set_viewport_size(previous)


def assert_matchup_comparison(page,shots):
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(BASE+'/#archive?year=2026&region=4&view=actual');page.reload()
    expect(page.locator('.game')).to_have_count(3)
    page.locator('#draw-bracket').click()
    expect(page.locator('[data-view="sample"]')).to_have_attribute('aria-pressed','true')
    page.locator('.game').first.click()
    expect(page.locator('dialog').get_by_role('link',name='Compare saved forecasts →')).to_have_count(0)
    page.keyboard.press('Escape')
    page.locator('[data-view="actual"]').click()
    championship=page.locator('[data-game="2026-r6-0"]')
    championship.focus();page.keyboard.press('Enter')
    page.get_by_role('link',name='Compare saved forecasts →').focus();page.keyboard.press('Enter')
    panel=page.locator('#matchup-comparison')
    expect(page.locator('#compare-status')).to_have_text('2026 saved matchup comparison loaded.')
    expect(page.locator('#compare-year')).to_be_focused()
    expect(page.locator('#compare-game')).to_have_value('2026-r6-0')
    expect(page.locator('dialog')).not_to_be_visible()
    expect(panel.locator('[data-forecast="seed"] [data-probability="a"]')).to_have_text('46.1%')
    expect(panel.locator('[data-forecast="seed_curve"] [data-probability="a"]')).to_have_text('39.9%')
    expect(panel.locator('[data-forecast="form"] [data-probability="a"]')).to_have_text('37.6%')
    expect(panel).to_contain_text('2,519 earlier games')
    expect(panel).to_contain_text('1,196 earlier games')
    expect(panel).to_contain_text('not uncertainty intervals')
    page.locator('#compare-swap').focus()
    for _ in range(7): page.keyboard.press('Enter')
    expect(page.locator('#compare-swap')).to_be_focused()
    expect(page.locator('#compare-swap')).to_have_attribute('aria-pressed','true')
    expect(panel.locator('[data-forecast="seed"] [data-probability="a"]')).to_have_text('53.9%')
    expect(panel.locator('[data-forecast="seed_curve"]')).to_contain_text('+6.2 percentage points vs baseline for Michigan')
    assert 'compare_side=b' in page.url
    panel.locator('.compare-game-heading').get_by_role('link',name='Michigan',exact=True).click()
    expect(page.locator('.team-profile h1')).to_have_text('Michigan')
    page.go_back();expect(page.locator('#compare-swap')).to_have_attribute('aria-pressed','true')
    page.locator('#compare-evidence').focus();page.keyboard.press('Enter')
    expect(page.locator('#insight-year')).to_have_value('2026')
    expect(page.locator('#insight-status')).to_have_text('2026 evidence loaded.')
    page.go_back();expect(page.locator('#compare-game')).to_have_value('2026-r6-0')
    page.go_back();expect(championship).to_be_focused()
    expect(page.locator('[data-view="actual"]')).to_have_attribute('aria-pressed','true')
    page.go_forward();expect(page.locator('#compare-status')).to_have_text('2026 saved matchup comparison loaded.')
    for selected in ('2026-r1-0','2026-r5-0','2026-r1-1','2026-r6-0'):
        page.select_option('#compare-game',selected)
    expect(page.locator('#compare-status')).to_have_text('2026 saved matchup comparison loaded.')
    expect(page.locator('#compare-game')).to_have_value('2026-r6-0')
    expect(panel.locator('[data-forecast="seed"] [data-probability="a"]')).to_have_text('46.1%')
    for selected in ('2026-r1-0','2026-r6-0','2026-r1-0','2026-r6-0'):
        page.select_option('#compare-game',selected)
        expect(page.locator('#compare-status')).to_have_text('2026 saved matchup comparison loaded.')
        expect(page.locator('#compare-game')).to_have_value(selected)
        expect(page.locator('#compare-swap')).to_have_attribute('aria-pressed','false')
        assert 'compare_game='+selected in page.url
    expect(panel.locator('[data-forecast="seed"] [data-probability="a"]')).to_have_text('46.1%')
    page.locator('#compare-game').focus();capture_comparison(page,shots,'populated')
    page.screenshot(path=str(shots/'matchup-comparison-page-desktop.png'),full_page=True)
    for width in (768,390,320):
        page.set_viewport_size({'width':width,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(shots/'matchup-comparison-page-mobile.png'),full_page=True)
    page.emulate_media(reduced_motion='reduce')
    assert page.locator('#compare-swap').evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s'
    page.select_option('#compare-year','1985')
    expect(page.locator('#compare-status')).to_have_text('1985 saved matchup comparison loaded.')
    expect(panel.locator('[data-probability="a"]')).to_have_text(['—','—','—'])
    expect(panel.locator('.forecast-strip')).to_have_count(0)
    expect(panel).to_contain_text('Training horizon —')
    capture_comparison(page,shots,'warm-up')
    page.select_option('#compare-year','2006')
    expect(page.locator('#compare-status')).to_have_text('2006 saved matchup comparison loaded.')
    expect(panel.locator('[data-forecast="form"]')).to_contain_text('Form features exist')
    expect(panel.locator('[data-forecast="form"] [data-probability="a"]')).to_have_text('—')
    page.select_option('#compare-year','2021')
    expect(page.locator('#compare-status')).to_have_text('2021 saved matchup comparison loaded.')
    page.select_option('#compare-game','2021-r1-21')
    expect(page.locator('#compare-status')).to_have_text('2021 no-contest record loaded.')
    expect(panel.locator('[data-probability="a"]')).to_have_text(['—','—','—'])
    expect(panel).to_contain_text('Recorded advancement: Oregon')
    capture_comparison(page,shots,'no-contest')
    page.locator('#compare-swap').click()
    expect(page.locator('#compare-swap')).to_have_attribute('aria-pressed','true')
    page.select_option('#compare-year','2020')
    expect(panel).to_contain_text('TOURNAMENT CANCELLED')
    expect(panel.locator('.forecast-card')).to_have_count(0)
    expect(page.locator('#compare-game')).to_be_disabled()
    expect(page.locator('#compare-swap')).to_be_disabled()
    expect(page.locator('#compare-swap')).to_have_attribute('aria-pressed','false')
    assert page.url.endswith('#matchup?compare_year=2020')
    capture_comparison(page,shots,'empty')
    page.locator('#compare-evidence').focus();page.keyboard.press('Enter')
    expect(page.locator('#insight-year')).to_have_value('2020')
    expect(page.locator('#insight-status')).to_have_text('2020 evidence loaded.')
    expect(page.locator('#insight-content')).to_contain_text('TOURNAMENT CANCELLED')
    page.go_back();expect(page.locator('#compare-status')).to_have_text('2020 tournament cancelled.')
    expect(page.locator('#compare-year')).to_have_value('2020')
    expect(page.locator('#compare-swap')).to_be_disabled()
    expect(page.locator('#compare-swap')).to_have_attribute('aria-pressed','false')
    expect(panel.locator('.forecast-card')).to_have_count(0)
    assert page.url.endswith('#matchup?compare_year=2020')
    page.emulate_media(reduced_motion='no-preference')
    # Clear static caches for controlled loading/failure and delayed-response tests.
    page.goto(BASE+'/#matchup?compare_year=2026&compare_game=2026-r6-0');page.reload()
    expect(page.locator('#compare-status')).to_have_text('2026 saved matchup comparison loaded.')
    page.locator('#compare-swap').click()
    expect(page.locator('#compare-swap')).to_have_attribute('aria-pressed','true')
    pending=[]
    path='**/data/seasons/1996.json' if STATIC else '**/api/season?year=1996'
    page.route(path,lambda route:pending.append(route))
    page.select_option('#compare-year','1996')
    expect(page.locator('#compare-content')).to_have_attribute('aria-busy','true')
    expect(panel.locator('.forecast-card')).to_have_count(0)
    expect(page.locator('#compare-swap')).to_have_attribute('aria-pressed','false')
    capture_comparison(page,shots,'loading')
    page.select_option('#compare-year','2006')
    expect(page.locator('#compare-status')).to_have_text('2006 saved matchup comparison loaded.')
    assert len(pending)==1
    pending[0].continue_();page.wait_for_load_state('networkidle');page.unroute(path)
    expect(page.locator('#compare-year')).to_have_value('2006')
    expect(page.locator('#compare-status')).to_have_text('2006 saved matchup comparison loaded.')
    path='**/data/seasons/1997.json' if STATIC else '**/api/season?year=1997'
    page.route(path,lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Controlled comparison outage"}'))
    page.select_option('#compare-year','1997')
    expect(panel.get_by_role('heading',name='Comparison unavailable')).to_be_visible()
    expect(panel.locator('.forecast-card')).to_have_count(0)
    capture_comparison(page,shots,'error')
    page.unroute(path);page.get_by_role('button',name='Retry comparison').focus();page.keyboard.press('Enter')
    expect(page.locator('#compare-status')).to_have_text('1997 saved matchup comparison loaded.')
    # A shared delayed static table or delayed local forecasts must render the latest game.
    path='**/data/tables/2008.json' if STATIC else '**/api/predict?year=2008&*'
    pending=[];page.route(path,lambda route:pending.append(route))
    page.select_option('#compare-year','2008')
    expect(page.locator('#compare-game')).to_be_enabled()
    expect(page.locator('#compare-status')).to_have_text('Loading 2008 comparison…')
    page.select_option('#compare-game','2008-r6-0')
    expect(page.locator('#compare-game')).to_have_value('2008-r6-0')
    assert len(pending)==(1 if STATIC else 6)
    for route in pending:
        route.continue_()
    page.wait_for_load_state('networkidle');page.unroute(path)
    expect(page.locator('#compare-status')).to_have_text('2008 saved matchup comparison loaded.')
    expect(panel.locator('.compare-game-heading')).to_contain_text('Championship')
    expect(page.locator('#compare-game')).to_have_value('2008-r6-0')
    expect(panel.locator('[data-forecast="seed"] [data-probability="a"]')).to_have_text('50.0%')
    expect(panel.locator('[data-forecast="seed_curve"] [data-probability="a"]')).to_have_text('50.0%')
    # Leaving during a delayed season fetch cannot resurrect the comparison route.
    path='**/data/seasons/1998.json' if STATIC else '**/api/season?year=1998'
    pending=[];page.route(path,lambda route:pending.append(route))
    page.select_option('#compare-year','1998')
    expect(page.locator('#compare-status')).to_have_text('Loading 1998 comparison…')
    page.locator('nav').get_by_role('link',name='Data & method').click()
    expect(page.get_by_role('heading',name='Know the data')).to_be_visible()
    pending[0].continue_();page.wait_for_load_state('networkidle');page.unroute(path)
    expect(page.get_by_role('heading',name='Know the data')).to_be_visible()
    expect(panel).to_have_count(0)


def run():
    command=[sys.executable,'-m','http.server','8037','--bind','127.0.0.1','--directory','public'] if STATIC else [sys.executable,'-m','madness','serve','--port','8037']
    proc=subprocess.Popen(command,cwd=ROOT,
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(BASE+('/data/summary.json' if STATIC else '/api/summary'),timeout=1).close();break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('Local server did not start')
        shots=ROOT/'docs/screenshots';shots.mkdir(exist_ok=True,parents=True)
        with sync_playwright() as p:
            channel=os.environ.get('MARCH_BROWSER_CHANNEL','msedge')
            browser=p.chromium.launch(headless=True,**({} if channel=='chromium' else {'channel':channel}))
            page=browser.new_page(viewport={'width':1440,'height':1000})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(BASE);expect(page.get_by_role('heading',name='March 2027',exact=True)).to_be_visible()
            expect(page.get_by_text('FIELD NOT ANNOUNCED',exact=True)).to_be_visible()
            page.screenshot(path=str(shots/'2027-desktop.png'),full_page=True)
            page.locator('nav').get_by_role('link',name='Historical bracket').click()
            expect(page.locator('.game')).to_have_count(15)
            assert_skip_preserves_archive(page)
            page.locator('.game').first.focus();page.keyboard.press('Enter')
            expect(page.locator('dialog')).to_be_visible();expect(page.locator('#detail-title')).to_contain_text('Duke')
            page.select_option('#detail-model','form');expect(page.locator('#detail-prediction')).to_contain_text('trained through 2025')
            expect(page.locator('dialog')).to_contain_text('verified against SportsDataverse/ESPN')
            page.keyboard.press('Escape');expect(page.locator('dialog')).not_to_be_visible()
            assert page.locator('.game').first.evaluate('(e)=>e===document.activeElement')
            page.get_by_role('button',name='Final Four',exact=True).click();expect(page.locator('.game')).to_have_count(3)
            page.get_by_role('button',name='Region 1',exact=True).click()
            page.screenshot(path=str(shots/'archive-desktop.png'),full_page=True)
            page.get_by_role('button',name='Simulate this field',exact=True).click()
            expect(page.get_by_role('heading',name='Advancement probabilities · 2026')).to_be_visible(timeout=15000)
            expect(page.get_by_role('button',name='Actual results',exact=True)).to_be_visible()
            assert_skip_preserves_archive(page)
            page.select_option('#archive-year','2021');expect(page.get_by_text('62',exact=True)).to_be_visible()
            page.get_by_role('button',name='Region 3',exact=True).click()
            page.get_by_role('button',name='Oregon versus VCU, Round of 64, open details').click()
            expect(page.locator('dialog')).to_contain_text('NO CONTEST');page.keyboard.press('Escape')
            page.select_option('#archive-year','1985');expect(page.locator('.bracket-key')).to_contain_text('warm-up')
            page.locator('nav').get_by_role('link',name='Matchup lab').click()
            expect(page.locator('#matchup-result .probability')).to_have_count(2)
            page.fill('#seed-a','8');page.fill('#seed-b','8');page.get_by_role('button',name='Compare seeds').click()
            expect(page.locator('#matchup-result')).to_contain_text('50.0%')
            page.locator('nav').get_by_role('link',name='Model evidence').click()
            expect(page.get_by_role('heading',name='2021–2026 holdout')).to_be_visible()
            expect(page.locator('svg[role="img"]')).to_be_visible()
            assert_season_evidence(page,shots)
            assert_insight_request_states(page,shots)
            if STATIC:
                message=page.evaluate("async()=>{const {request}=await import('./static_api.js');try{await request('/api/simulate?year=2027')}catch(e){return e.message}}")
                assert 'unknown' in message
                message=page.evaluate("async()=>{const {request}=await import('./static_api.js');try{await request('/api/predict?a=17&b=1')}catch(e){return e.message}}")
                assert 'Seeds' in message
            else:
                r=page.request.get(BASE+'/api/simulate?year=2027');assert r.status==400 and 'unknown' in r.json()['error']
                r=page.request.get(BASE+'/api/predict?a=17&b=1');assert r.status==400
            page.locator('nav').get_by_role('link',name='2027 tournament').click()
            page.set_input_files('#field-file',{'name':'invalid.json','mimeType':'application/json','buffer':b'{"season":2027,"status":"announced","slots":[]}'} )
            expect(page.locator('#import-status')).to_contain_text('64 main-bracket slots')
            # Generated structural fixture stays in memory; it is never labeled or stored as actual 2027 data.
            archive=json.loads((ROOT/'data/derived/archive.json').read_text())['2026']
            slots=[[dict(id=t['id'],name=t['name'],seed=t['seed'])] for t in archive['teams']]
            for i in range(12):
                slots[i].append(dict(id=f'test-only-{i}',name=f'Test only {i}',seed=slots[i][0]['seed']))
            field=dict(season=2027,status='test_only',expected_teams=76,expected_opening_games=12,slots=slots)
            page.set_input_files('#field-file',{'name':'test-only.json','mimeType':'application/json','buffer':json.dumps(field).encode()})
            expect(page.get_by_role('heading',name='Imported 2027 bracket')).to_be_visible(timeout=15000)
            expect(page.locator('#import-result .game')).to_have_count(15)
            page.locator('#import-result .game').first.click();expect(page.locator('dialog')).to_contain_text('locally imported field');page.keyboard.press('Escape')
            page.set_viewport_size({'width':768,'height':1024})
            page.goto(BASE+'/#archive');expect(page.locator('.game')).to_have_count(15)
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.set_viewport_size({'width':390,'height':844})
            page.goto(BASE+'/#archive');expect(page.locator('.game')).to_have_count(15)
            page.select_option('#archive-year','2026');expect(page.locator('.stat').first).to_contain_text('Michigan')
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert page.locator('.game:visible').count()==8
            page.select_option('#mobile-round','1');assert page.locator('.game:visible').count()==4
            assert_skip_preserves_archive(page)
            page.select_option('#mobile-round','0')
            page.screenshot(path=str(shots/'archive-mobile.png'),full_page=True)
            page.locator('.game').first.click();expect(page.locator('dialog')).to_be_visible()
            assert page.locator('dialog').bounding_box()['width']<=390
            page.keyboard.press('Escape')
            assert_team_profiles(page,shots)
            assert_profile_navigation_regressions(page)
            assert_matchup_comparison(page,shots)
            assert_team_scouting(page,shots,BASE,STATIC)
            assert_theme_journeys(browser,shots,BASE,STATIC)
            assert_bracket_drilldowns(browser,shots,BASE,STATIC)
            assert not errors,errors
            browser.close()
        print('Browser checks passed: desktop/mobile archive and profiles, exact identity separation, honest aggregates, missing history/cancelled/no-contest, origin-year/region/round/focus, keyboard dialog/back/forward/retry, same-year actual links, per-year sampled draw preservation, changed-control history, delayed simulation success/failure, table scrolling, reduced motion, stale requests, recorded model comparisons/swap/loading/empty/error/profile/evidence links, historical scouting windows/field percentiles/prior-only expectations, season evidence, simulation, matchup and import validation; shared light/dark palettes across complete journeys, saved/system themes, first loading frame, contrast samples and storage fallback; bracket drilldown request ownership, latest model, loading/current errors/retry and delayed success/failure.')
    finally:
        proc.terminate();proc.wait(timeout=10)


if __name__=='__main__':run()
