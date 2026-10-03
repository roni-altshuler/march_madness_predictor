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
        print('Browser checks passed: desktop, mobile, archive, skip-link focus/state, keyboard dialog, no-contest, simulation, matchup, evidence, unknown field and validation errors.')
    finally:
        proc.terminate();proc.wait(timeout=10)


if __name__=='__main__':run()
