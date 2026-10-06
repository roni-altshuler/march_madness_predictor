"""Real Edge smoke test. Run separately: python tests/browser_check.py."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

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
            assert not errors,errors
            browser.close()
        print('Browser checks passed: desktop, mobile, archive, skip-link focus/state, keyboard dialog, no-contest, simulation, matchup, season coverage/training/evaluation, cancelled/loading/error states, archive handoff, back/forward, narrow-table keyboard scroll, reduced motion, stale-response guard, request retry, unknown field and validation errors.')
    finally:
        proc.terminate();proc.wait(timeout=10)


if __name__=='__main__':run()
