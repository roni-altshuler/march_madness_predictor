"""Historical bracket round and keyboard-focus continuity in the real browser."""
import json
from playwright.sync_api import expect
from bracket_drilldown_browser import wait_pending


def assert_bracket_navigation(browser, shots, base, static):
    report=[]
    for viewport,width in [('mobile',390),('desktop',1440)]:
        context=browser.new_context(viewport={'width':width,'height':844})
        page=context.new_page();errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base+'/#archive?year=2026&region=0&view=actual&round=3')
        expect(page.locator('.game')).to_have_count(15)

        def check_round(value,label):
            expect(page.locator('#mobile-round')).to_have_value(str(value))
            expect(page.locator('.round-column.mobile-selected h3')).to_have_text(label)
            assert 'round='+str(value+(5 if page.locator('[data-region="4"]').get_attribute('aria-pressed')=='true' else 1)) in page.url
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            if page.viewport_size['width']<=720:
                assert page.locator('.round-column:visible').count()==1
                expect(page.locator('.round-column.mobile-selected')).to_be_visible()

        def state():
            return page.evaluate('''() => ({year:document.querySelector('#archive-year').value,region:document.querySelector('[data-region][aria-pressed="true"]').dataset.region,round:document.querySelector('#mobile-round').selectedOptions[0].textContent,focused_control:document.activeElement.dataset.region||document.activeElement.id||document.activeElement.tagName,url:location.hash})''')

        def region(value):
            button=page.locator(f'[data-region="{value}"]')
            button.focus();page.keyboard.press('Enter')
            expect(button).to_have_attribute('aria-pressed','true')
            expect(button).to_be_focused()

        # Native round chooser, repeat region changes, two separate stage memories.
        check_round(2,'Sweet 16')
        if viewport=='mobile':
            page.locator('#mobile-round').focus();page.keyboard.press('ArrowDown');page.keyboard.press('Enter')
            check_round(3,'Elite Eight');expect(page.locator('#mobile-round')).to_be_focused()
            page.select_option('#mobile-round','2')
        for selected in [1,2,3,0,1]:region(selected);check_round(2,'Sweet 16')
        page.locator('#season-content').screenshot(path=str(shots/f'bracket-navigation-region-{viewport}.png'))
        regional_state=state()
        region(4);check_round(0,'Final Four')
        if viewport=='mobile':page.select_option('#mobile-round','1')
        else:
            page.locator('.round-column[data-column="1"] .game').click();page.keyboard.press('Escape')
        check_round(1,'Championship')
        region(2);check_round(2,'Sweet 16')
        region(4);check_round(1,'Championship')
        for check_width in [320,390,720,721,768,1440]:
            page.set_viewport_size({'width':check_width,'height':844});check_round(1,'Championship')
        page.set_viewport_size({'width':width,'height':844})
        page.locator('#season-content').screenshot(path=str(shots/f'bracket-navigation-finals-{viewport}.png'))
        finals_state=state()
        region(0);check_round(2,'Sweet 16')
        report.append(dict(viewport=viewport,case='region repetition, separate regional/finals choices, keyboard controls and responsive breakpoint',widths=[320,390,720,721,768,1440],regional_state=regional_state,finals_state=finals_state,page_errors=errors))

        # Escape/button close and reopening preserve the exact originating card.
        card=page.locator('.round-column.mobile-selected .game').first
        for close in ['Escape','button','Escape']:
            card.focus();page.keyboard.press('Enter')
            expect(page.locator('dialog')).to_be_visible()
            expect(page.locator('#detail-body .eyebrow')).to_contain_text('Sweet 16')
            expect(page.locator('dialog .tag')).to_have_text('HISTORICAL RESULT')
            if close=='Escape':page.keyboard.press('Escape')
            else:page.locator('#close-detail').click()
            expect(card).to_be_focused();check_round(2,'Sweet 16')
        card.focus();page.keyboard.press('Enter')
        page.locator('#detail-title a').first.focus();page.keyboard.press('Enter')
        expect(page.locator('#profile-year')).to_have_value('2026')
        assert 'from_round=3' in page.url
        page.locator('.profile-back').focus();page.keyboard.press('Enter')
        expect(card).to_be_focused();check_round(2,'Sweet 16')
        page.go_back();expect(page.locator('#profile-year')).to_have_value('2026')
        page.go_forward();expect(card).to_be_focused();check_round(2,'Sweet 16')
        page.locator('nav a[href="#about"]').focus();page.keyboard.press('Enter')
        expect(page.get_by_role('heading',name='Know the data')).to_be_visible()
        page.go_back();check_round(2,'Sweet 16');expect(card).to_be_focused()
        page.go_forward();expect(page.get_by_role('heading',name='Know the data')).to_be_visible()
        page.go_back();check_round(2,'Sweet 16')
        report.append(dict(viewport=viewport,case='repeated close/reopen, profile return, browser Back/Forward and originating game focus',state=state(),page_errors=errors))

        # Historical years retain regional choice; no invented warm-up probabilities.
        for selected in ['2025','1985','2026']:
            page.locator('#archive-year').focus();page.select_option('#archive-year',selected)
            expect(page.locator('.game')).to_have_count(15)
            expect(page.locator('#archive-year')).to_be_focused();check_round(2,'Sweet 16')
            if selected=='1985':
                assert page.locator('.game-prob').all_text_contents()==['—']*15
                expect(page.locator('#draw-bracket')).to_be_disabled()
                page.locator('.round-column.mobile-selected .game').first.click()
                expect(page.locator('#detail-model')).to_have_count(0)
                assert page.locator('dialog .probability').all_text_contents()==['—','—']
                page.keyboard.press('Escape')
        # Preserve this round across actual/simulated view redraws without relabeling history.
        page.locator('#draw-bracket').click()
        expect(page.locator('[data-view="sample"]')).to_have_attribute('aria-pressed','true',timeout=15000)
        check_round(2,'Sweet 16');expect(page.locator('.bracket-key')).to_contain_text('one simulated draw')
        page.locator('.round-column.mobile-selected .game').first.click()
        expect(page.locator('dialog .tag')).to_have_text('SIMULATED DRAW');page.keyboard.press('Escape')
        for selected in ['actual','sample','actual']:
            button=page.locator(f'[data-view="{selected}"]');button.focus();page.keyboard.press('Enter')
            expect(button).to_be_focused();check_round(2,'Sweet 16')
        expect(page.locator('.bracket-key')).to_contain_text('Actual winner')
        page.reload();check_round(2,'Sweet 16')
        expect(page.locator('.bracket-key')).to_contain_text('Actual winner')
        report.append(dict(viewport=viewport,case='historical-year focus, warm-up dashes, actual/simulated distinction and reload',state=state(),page_errors=errors))

        # Deep links normalize invalid rounds; an explicit game takes precedence.
        for query,value,label in [('region=4&round=3',0,'Final Four'),('region=0&round=6',0,'Round of 64'),('region=0&round=bad',0,'Round of 64'),('region=0&round=1&game=2026-r3-0',2,'Sweet 16')]:
            page.goto(base+'/#archive?year=2026&view=actual&'+query)
            expect(page.locator('.game')).to_have_count(3 if query.startswith('region=4') else 15)
            check_round(value,label)
        expect(page.locator('[data-game="2026-r3-0"]')).to_be_focused()
        assert not errors,errors
        report.append(dict(viewport=viewport,case='round deep links, invalid inputs and game precedence',page_errors=errors))
        context.close()

        # A delayed older season cannot undo the latest year/round/focus selection.
        context=browser.new_context(viewport={'width':width,'height':844});page=context.new_page();errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base+'/#archive?year=2026&region=0&view=actual&round=3')
        expect(page.locator('.game')).to_have_count(15)
        path='**/data/seasons/2025.json' if static else '**/api/season?year=2025'
        pending=[];page.route(path,lambda route:pending.append(route))
        page.select_option('#archive-year','2025');wait_pending(page,pending,1)
        expect(page.locator('#archive-year')).to_be_focused()
        expect(page.locator('#season-content')).to_contain_text('Loading 2025 bracket')
        page.select_option('#archive-year','1985');expect(page.locator('.game')).to_have_count(15)
        expect(page.locator('#archive-year')).to_be_focused();check_round(2,'Sweet 16')
        region(1);check_round(2,'Sweet 16')
        pending[0].continue_();page.wait_for_load_state('networkidle');page.unroute(path)
        expect(page.locator('#archive-year')).to_have_value('1985')
        expect(page.locator('[data-region="1"]')).to_be_focused();check_round(2,'Sweet 16')
        assert page.locator('.game-prob').all_text_contents()==['—']*15
        page.locator('#season-content').screenshot(path=str(shots/f'bracket-navigation-interrupted-{viewport}.png'))
        assert not errors,errors
        report.append(dict(viewport=viewport,case='interrupted year request and latest region/round/focus ownership',year=1985,round=3,state=state(),page_errors=errors))
        context.close()
    (shots/f'bracket-navigation-{"static" if static else "api"}-report.json').write_text(json.dumps(dict(mode='static' if static else 'api',cases=report),indent=2)+'\n')
