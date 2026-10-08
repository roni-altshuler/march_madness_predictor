"""Actual-browser scouting story: recorded matchup -> profile -> prior evidence."""
import hashlib
import time
from urllib.parse import parse_qs, urlsplit
from playwright.sync_api import expect


def capture_scouting(page, shots, state, selector='#team-scouting'):
    previous=page.viewport_size
    for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator(selector).screenshot(path=str(shots/f'team-scouting-{state}-{name}.png'))
    page.set_viewport_size(previous)


def assert_team_scouting(page, shots, base, static):
    def params():
        return parse_qs(urlsplit(page.url).fragment.split('?')[1])

    def prior_years():
        return page.locator('[data-scout-year]').evaluate_all('(elements)=>elements.map(e=>Number(e.dataset.scoutYear))')

    for width,height in [(1440,1000),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        page.goto(base+'/#archive?year=2026&region=0&view=actual')
        card=page.locator('[data-game="2026-r1-0"]')
        card.focus();page.keyboard.press('Enter')
        page.locator('dialog').get_by_role('link',name='Duke',exact=True).focus();page.keyboard.press('Enter')
        dossier=page.locator('#team-scouting')
        expect(dossier.get_by_role('heading',name='Before the 2026 tournament')).to_be_visible()
        expect(page.locator('#scout-window')).to_have_value('5')
        assert prior_years()==[2025,2024,2023,2022,2019]
        expect(page.locator('[data-scout-total="wins"]')).to_have_text('15')
        expect(page.locator('[data-scout-total="expected"]')).to_have_text('13.53')
        expect(page.locator('[data-scout-total="difference"]')).to_have_text('+1.47')
        expect(dossier.locator('[data-scout-metric="elo"]')).to_contain_text('1,694.9')
        expect(dossier.locator('[data-scout-metric="elo"]')).to_contain_text('Field percentile 96.1')
        expect(dossier).to_contain_text('29 completed games · frozen 2026-03-01, 00:00 UTC')
        assert params()['from_game']==['2026-r1-0']
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#scout-window').focus();page.keyboard.press('Home');page.keyboard.press('Enter')
        expect(page.locator('#scout-window')).to_have_value('3')
        expect(page.locator('#scout-window')).to_be_focused()
        assert params()['scout_window']==['3'] and prior_years()==[2025,2024,2023]
        expect(page.locator('[data-scout-total="wins"]')).to_have_text('8')
        page.reload();expect(page.locator('#scout-window')).to_have_value('3')
        dossier.get_by_role('link',name='2025 matchups →').focus();page.keyboard.press('Enter')
        expect(page.locator('#compare-year')).to_have_value('2025')
        expect(page.locator('#compare-game')).to_have_value('2025-r1-16')
        page.go_back();expect(page.locator('#scout-window')).to_have_value('3')
        assert prior_years()==[2025,2024,2023] and params()['appearance']==['2026']
        for window in ['all','5','3','all','5']:
            page.select_option('#scout-window',window)
            assert params()['scout_window']==[window]
            assert all(year<2026 for year in prior_years())
            assert len(prior_years())==({'3':3,'5':5,'all':18}[window])
        for selected in ['2015','2026','2006','2026']:
            page.select_option('#profile-year',selected)
            expect(dossier.get_by_role('heading',name=f'Before the {selected} tournament')).to_be_visible()
            assert params()['appearance']==[selected] and params()['scout_window']==['5']
            assert all(year<int(selected) for year in prior_years())
        expect(page.locator('[data-scout-total="expected"]')).to_have_text('13.53')
        page.locator('#scout-window').focus()
        if width==1440: capture_scouting(page,shots,'populated')
        page.select_option('#profile-year','2006')
        expect(dossier).to_contain_text('No earlier appearances in this identity')
        expect(page.locator('[data-scout-total="expected"]')).to_have_text('—')
        expect(dossier.locator('.scout-percentile')).to_have_count(3)
        if width==1440: capture_scouting(page,shots,'no-prior')
        page.locator('.profile-back').focus();page.keyboard.press('Enter')
        expect(page.locator('#archive-year')).to_have_value('2026')
        expect(card).to_be_focused()
        expect(page.locator('.bracket-key')).to_contain_text('Actual winner')
        page.go_back();expect(page.locator('#profile-year')).to_have_value('2006')
        expect(page.locator('#scout-window')).to_have_value('5')

        page.goto(base+'/#team?profile=archive%3ADuke&from=2026&appearance=1990&scout_window=all')
        expect(dossier.get_by_role('heading',name='Before the 1990 tournament')).to_be_visible()
        expect(dossier).to_contain_text('no saved earlier-trained seed forecasts')
        expect(dossier.locator('.scout-metric strong')).to_have_text(['—','—','—'])
        expect(dossier.locator('.scout-percentile')).to_have_count(0)
        assert all(year<1990 for year in prior_years())
        if width==1440: capture_scouting(page,shots,'warm-up')
        page.goto(base+'/#team?profile=espn%3A2670&from=2026&appearance=2025&scout_window=all')
        expect(dossier.get_by_role('heading',name='Before the 2025 tournament')).to_be_visible()
        expect(dossier).to_contain_text('1 no-contest entries excluded')
        expect(dossier.locator('[data-scout-year="2021"]')).to_contain_text('0 / 0')
        expect(dossier.locator('[data-scout-year="2021"] td').last).to_have_text('—')
        page.goto(base+'/#team?profile=espn%3A150&from=2026&appearance=2020')
        expect(dossier.get_by_role('heading',name='Scouting unavailable for 2020')).to_be_visible()
        expect(dossier).to_contain_text('The tournament was cancelled.')
        expect(dossier.locator('.scout-metrics,.scout-totals')).to_have_count(0)
        if width==1440: capture_scouting(page,shots,'cancelled')
        page.goto(base+'/#team?profile=espn%3A150&from=2026&appearance=2027')
        expect(dossier.get_by_role('heading',name='Scouting unavailable for 2027')).to_be_visible()
        expect(dossier).to_contain_text('does not establish qualification')
        expect(page.locator('#scout-window')).to_have_count(0)

        profile_path='**/data/teams/'+hashlib.sha256(b'espn:150').hexdigest()+'.json' if static else '**/api/team?profile=espn%3A150'
        page.route(profile_path,lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Controlled scouting outage"}'))
        page.goto(base+'/#team?profile=espn%3A150&from=2026&appearance=2026&scout_window=3');page.reload()
        expect(page.get_by_role('heading',name='Team history unavailable')).to_be_visible()
        expect(dossier).to_have_count(0)
        if width==1440: capture_scouting(page,shots,'error','.team-profile')
        page.unroute(profile_path)
        page.get_by_role('button',name='Retry team history',exact=True).focus();page.keyboard.press('Enter')
        expect(page.locator('#scout-window')).to_have_value('3')
        assert prior_years()==[2025,2024,2023]
        pending=[];page.route(profile_path,lambda route:pending.append(route))
        page.reload()
        expect(page.locator('.profile-empty')).to_contain_text('scouting evidence')
        # Static mode awaits its profile index before requesting this file.
        deadline=time.monotonic()+5
        while not pending and time.monotonic()<deadline:
            page.wait_for_timeout(10)
        if width==1440: capture_scouting(page,shots,'loading','.team-profile')
        assert len(pending)==1, {'pending_requests':len(pending),'static':static,'width':width,'url':page.url,'profile_path':profile_path}
        page.goto(base+'/#team?profile=espn%3A130&from=2026&appearance=2026')
        expect(page.locator('.team-profile h1')).to_have_text('Michigan')
        expect(dossier.get_by_role('heading',name='Before the 2026 tournament')).to_be_visible()
        for window in ['3','all','5']: page.select_option('#scout-window',window)
        content=page.locator('main').inner_html()
        for route in pending: route.continue_()
        page.wait_for_load_state('networkidle');page.unroute(profile_path)
        assert page.locator('main').inner_html()==content
        expect(page.locator('.team-profile h1')).to_have_text('Michigan')
        assert params()['profile']==['espn:130'] and params()['scout_window']==['5']
        page.emulate_media(reduced_motion='reduce')
        assert page.locator('#scout-window').evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s'
        page.emulate_media(reduced_motion='no-preference')
        if width==390:
            table=dossier.get_by_role('region',name='Earlier tournament scouting evidence, scroll horizontally')
            table.focus();page.keyboard.press('ArrowRight')
            page.wait_for_function('document.querySelector("#team-scouting .profile-table-scroll").scrollLeft>0')
        for check_width in [768,390,320]:
            page.set_viewport_size({'width':check_width,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.set_viewport_size({'width':width,'height':height})
