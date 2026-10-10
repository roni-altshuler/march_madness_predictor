"""Browser regression for late probability responses in bracket matchup dialogs."""
import json
import time
from playwright.sync_api import expect


def wait_pending(page, pending, count):
    deadline=time.monotonic()+5
    while len(pending)<count and time.monotonic()<deadline:
        page.wait_for_timeout(10)
    assert len(pending)==count


def open_game(page, year=2026):
    card=page.locator(f'[data-game="{year}-r1-0"]')
    expect(card).to_be_visible()
    card.focus();page.keyboard.press('Enter')
    expect(page.locator('dialog')).to_be_visible()


def capture_dialog(page, shots, state, viewport):
    page.locator('dialog').evaluate('(element)=>element.scrollTop=0')
    page.locator('dialog').screenshot(path=str(shots/f'bracket-drilldown-{state}-title-{viewport}.png'))
    page.locator('#detail-model').scroll_into_view_if_needed()
    page.locator('dialog').screenshot(path=str(shots/f'bracket-drilldown-{state}-result-{viewport}.png'))


def assert_bracket_drilldowns(browser, shots, base, static):
    report=[]
    path='**/data/tables/2026.json' if static else '**/api/predict?year=2026&*'
    for viewport,width,height in [('desktop',1440,1000),('mobile',390,844)]:
        def new_page():
            context=browser.new_context(viewport={'width':width,'height':height})
            page=context.new_page();errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(base+'/#archive?year=2026&region=0&view=actual')
            expect(page.locator('.game')).to_have_count(15)
            return context,page,errors

        for late in ['success','failure']:
            context,page,errors=new_page();pending=[]
            page.route(path,lambda route:pending.append(route))
            open_game(page);page.locator('#detail-model').focus()
            page.select_option('#detail-model','form')
            expect(page.locator('#detail-prediction')).to_have_attribute('aria-busy','true')
            expect(page.locator('#detail-prediction')).to_have_text('Loading pre-March form challenger probability…',ignore_case=True)
            expect(page.locator('#detail-model')).to_be_focused()
            wait_pending(page,pending,1)
            if late=='success':
                page.locator('#detail-model').scroll_into_view_if_needed()
                page.locator('dialog').screenshot(path=str(shots/f'bracket-drilldown-loading-{viewport}.png'))
            page.keyboard.press('Escape');expect(page.locator('dialog')).not_to_be_visible()
            expect(page.locator('[data-game="2026-r1-0"]')).to_be_focused()
            page.select_option('#archive-year','2025');open_game(page,2025)
            page.select_option('#detail-model','seed_curve')
            result=page.locator('#detail-prediction')
            expect(result).to_have_text('Seed curve challenger · Auburn 91.5% · Alabama State 8.5% · trained through 2024')
            expected=result.inner_text()
            if late=='success':pending[0].continue_()
            else:pending[0].fulfill(status=503,content_type='application/json',body='{"error":"Controlled late comparison failure"}')
            page.wait_for_load_state('networkidle');page.unroute(path)
            expect(result).to_have_text(expected);expect(result).not_to_have_attribute('aria-busy','true')
            expect(page.locator('#detail-title')).to_have_text('Auburn vs Alabama State')
            expect(page.locator('#detail-model')).to_have_value('seed_curve')
            assert not errors,errors
            if late=='success':capture_dialog(page,shots,'after',viewport)
            report.append(dict(viewport=viewport,case='late '+late,year=2025,title='Auburn vs Alabama State',result=expected,page_errors=errors))
            context.close()

        # Rapid model changes: older success/error cannot replace the latest seed choice.
        context,page,errors=new_page();pending=[]
        page.route(path,lambda route:pending.append(route));open_game(page)
        page.evaluate('''() => {
          window.predictionMessages=[];
          new MutationObserver(records=>records.forEach(record=>record.addedNodes.forEach(node=>{
            if(node.textContent.includes('trained through'))predictionMessages.push(node.textContent);
          }))).observe(document.querySelector('#detail-prediction'),{childList:true});
        }''')
        page.locator('#detail-model').focus()
        for kind,label in [('form','pre-March form challenger'),('seed_curve','seed curve challenger'),('seed','seed baseline')]:
            page.select_option('#detail-model',kind)
            expect(page.locator('#detail-prediction')).to_have_text(f'Loading {label} probability…',ignore_case=True)
            expect(page.locator('#detail-prediction')).to_have_attribute('aria-busy','true')
            expect(page.locator('#detail-model')).to_be_focused()
        wait_pending(page,pending,1 if static else 3)
        pending[-1].continue_()
        result=page.locator('#detail-prediction')
        expected='Seed baseline · Duke 91.4% · Siena 8.6% · trained through 2025'
        expect(result).to_have_text(expected)
        if not static:
            pending[1].fulfill(status=503,content_type='application/json',body='{"error":"Controlled older-model failure"}')
            pending[0].continue_()
        page.wait_for_load_state('networkidle');page.unroute(path)
        expect(result).to_have_text(expected);expect(result).not_to_have_attribute('aria-busy','true')
        assert page.evaluate('window.predictionMessages')==[expected]
        assert not errors,errors
        report.append(dict(viewport=viewport,case='rapid model choices',year=2026,result=expected,page_errors=errors))
        context.close()

        # A current failure stays explicit; a fresh choice retries without replacing controls.
        context,page,errors=new_page();pending=[]
        page.route(path,lambda route:pending.append(route));open_game(page)
        page.locator('#detail-model').focus();page.select_option('#detail-model','form')
        wait_pending(page,pending,1)
        pending[0].fulfill(status=503,content_type='application/json',body='{"error":"Controlled current comparison outage"}')
        result=page.locator('#detail-prediction')
        expect(result).to_contain_text('Pre-March form challenger: comparison unavailable.')
        expect(result).not_to_contain_text('trained through')
        expect(result).not_to_have_attribute('aria-busy','true')
        expect(page.locator('#detail-model')).to_be_focused()
        page.locator('dialog').screenshot(path=str(shots/f'bracket-drilldown-error-{viewport}.png'))
        page.unroute(path);page.select_option('#detail-model','seed_curve')
        expect(result).to_have_text('Seed curve challenger · Duke 92.2% · Siena 7.8% · trained through 2025')
        assert not errors,errors
        report.append(dict(viewport=viewport,case='current error and retry',year=2026,result=result.inner_text(),page_errors=errors))
        context.close()

        # Leaving a pending matchup cannot change its hidden status or the profile route.
        context,page,errors=new_page();pending=[]
        page.route(path,lambda route:pending.append(route));open_game(page)
        page.select_option('#detail-model','form');wait_pending(page,pending,1)
        page.locator('#detail-title').get_by_role('link',name='Duke',exact=True).focus();page.keyboard.press('Enter')
        expect(page.locator('#profile-year')).to_have_value('2026')
        expect(page.locator('dialog')).not_to_be_visible()
        content=page.locator('main').inner_html()
        pending[0].continue_();page.wait_for_load_state('networkidle');page.unroute(path)
        assert page.locator('main').inner_html()==content
        expect(page.locator('#detail-prediction')).to_have_text('Loading pre-March form challenger probability…',ignore_case=True)
        assert not errors,errors
        report.append(dict(viewport=viewport,case='leave to profile',year=2026,page_errors=errors))
        context.close()

        # Audit normal later-round navigation and seasons without a comparable probability.
        context,page,errors=new_page()
        if viewport=='mobile':page.select_option('#mobile-round','2')
        card=page.locator('.round-column[data-column="2"] .game').first
        card.focus();page.keyboard.press('Enter')
        expect(page.locator('#detail-body .eyebrow')).to_contain_text('Sweet 16')
        page.locator('#detail-title').get_by_role('link',name='Duke',exact=True).focus();page.keyboard.press('Enter')
        expect(page.locator('#profile-year')).to_have_value('2026')
        page.locator('.profile-back').focus();page.keyboard.press('Enter')
        expect(card).to_be_focused()
        if viewport=='mobile':expect(page.locator('#mobile-round')).to_have_value('2')
        page.select_option('#archive-year','1985');open_game(page,1985)
        expect(page.locator('#detail-model')).to_have_count(0)
        assert page.locator('dialog .probability').all_text_contents()==['—','—']
        expect(page.locator('dialog')).to_contain_text('warm-up era')
        page.keyboard.press('Escape');page.select_option('#archive-year','2021')
        expect(page.locator('[data-region="2"]')).to_be_visible();page.locator('[data-region="2"]').click()
        card=page.get_by_role('button',name='Oregon versus VCU, Round of 64, open details')
        card.focus();page.keyboard.press('Enter')
        expect(page.locator('dialog')).to_contain_text('NO CONTEST')
        expect(page.locator('#detail-model')).to_have_count(0)
        assert page.locator('dialog .probability').all_text_contents()==['—','—']
        page.keyboard.press('Escape')
        page.locator('nav').get_by_role('link',name='Model evidence').click()
        page.select_option('#insight-year','2020')
        expect(page.locator('#season-insights')).to_contain_text('2020 · no tournament played')
        expect(page.locator('#insight-archive')).to_have_count(0)
        page.locator('.brand').click()
        expect(page.get_by_text('FIELD NOT ANNOUNCED',exact=True)).to_be_visible()
        for check_width in [320,390,768,width]:
            page.set_viewport_size({'width':check_width,'height':height})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors,errors
        report.append(dict(viewport=viewport,case='later-round back, warm-up, no-contest, cancelled and unknown field',page_errors=errors))
        context.close()

    (shots/'bracket-drilldown-report.json').write_text(json.dumps(report,indent=2)+'\n')
