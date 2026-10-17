"""Track record: reconciliation, dates, keyboard/touch controls and request ownership."""
import copy
import json
from time import monotonic
from playwright.sync_api import expect


def assert_track_record(browser, shots, base, static):
    mode='static' if static else 'api';report=[]
    path='**/data/track_record.json' if static else '**/api/track-record'
    endpoint='/data/track_record.json' if static else '/api/track-record'
    for name,width,height in [('desktop',1440,1000),('mobile',390,844),('narrow',320,844)]:
        def fresh():
            context=browser.new_context(viewport=dict(width=width,height=height),reduced_motion='reduce')
            page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            return context,page,errors
        def finish(context,page,errors,case,**values):
            assert not errors,errors
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            report.append(dict(viewport=name,case=case,page_errors=errors,**values));context.close()

        context,page,errors=fresh();page.goto(base)
        expect(page.locator('.home-path .game')).to_have_count(15)
        strip=page.locator('.record-strip');expect(strip).to_contain_text('71.4%');expect(strip).to_contain_text('269 / 377')
        expect(strip).to_contain_text('Historical backtest');expect(strip).to_contain_text('Not yet scored')
        game=page.locator('.home-path .game:visible').first.bounding_box();assert game['y']+game['height']<=height,game
        strip.focus();page.keyboard.press('Enter')
        expect(page.get_by_role('heading',name='Track record',exact=True)).to_be_visible()
        expect(page.locator('#record-accuracy')).to_have_text('71.4%');expect(page.locator('#record-count')).to_contain_text('269 / 377')
        data=page.request.get(base+endpoint).json();historical=data['historical']
        assert historical['totals']['correct']==269 and historical['totals']['settled']==377
        assert data['prospective']['totals']['accuracy_pct'] is None
        assert historical['points'][-1]['cumulative']==historical['totals']
        assert page.locator('.record-chart').get_attribute('viewBox')=='0 0 720 280'
        assert '100%' in page.locator('.record-chart').text_content() and '0%' in page.locator('.record-chart').text_content()
        for button in page.locator('.record-tabs button,.record-point-buttons button,.record-pagination button').all():
            assert button.bounding_box()['height']>=44
        control=page.locator('#record-point');control.focus();page.keyboard.press('Home')
        expect(control).to_have_value('0');expect(page.locator('#record-point-detail')).to_contain_text(historical['points'][0]['week'])
        page.keyboard.press('End');expect(control).to_have_value(str(len(historical['points'])-1))
        expect(page.locator('#record-point-detail')).to_contain_text('269 / 377 correct · 71.4%')
        expect(page.locator('#record-point-detail')).to_contain_text('13 / 20 correct · 65.0%')
        page.keyboard.press('ArrowLeft');expect(control).to_have_value(str(len(historical['points'])-2))
        page.locator('[data-point-step="1"]').click();expect(control).to_have_value(str(len(historical['points'])-1))
        plot=page.locator('.record-chart').bounding_box();viewport=page.locator('.record-chart-scroll').bounding_box()
        assert plot['width']<=viewport['width']+.1
        selected=page.locator('.record-dot.selected').bounding_box()
        assert viewport['x']<=selected['x'] and selected['x']+selected['width']<=viewport['x']+viewport['width']
        for check_width in [320,390,720,721,768,1440]:
            page.set_viewport_size(dict(width=check_width,height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            plot=page.locator('.record-chart').bounding_box();viewport=page.locator('.record-chart-scroll').bounding_box()
            selected=page.locator('.record-dot.selected').bounding_box()
            assert plot['width']<=viewport['width']+.1,dict(width=check_width,plot=plot,viewport=viewport)
            assert viewport['x']<=selected['x'] and selected['x']+selected['width']<=viewport['x']+viewport['width']
        page.set_viewport_size(dict(width=width,height=height))
        expect(page.locator('#record-accuracy')).to_have_text('71.4%')
        page.locator('.record-calendar > summary').focus();page.keyboard.press('Enter')
        expect(page.locator('.record-calendar tbody tr')).to_have_count(24)
        expect(page.locator('.record-calendar tbody tr').last).to_contain_text('269 / 377')
        expect(page.locator('.record-calendar tbody tr').last).to_contain_text('13 / 20')
        page.locator('#record-next').click();expect(page.locator('#record-ledger')).to_contain_text('Showing 21–40.')
        page.locator('#record-prev').click();page.locator('#record-all').focus();page.keyboard.press('Enter')
        rows=page.locator('#record-ledger tbody tr');expect(rows).to_have_count(377)
        assert rows.evaluate_all('(rows)=>rows.filter(row=>row.children[4].textContent==="Yes · 1").length')==269
        assert rows.evaluate_all('(rows)=>rows.map(row=>row.dataset.recordId)')==[r['game_id'] for r in reversed(historical['records'])]
        rows.first.locator('summary').focus();page.keyboard.press('Enter')
        expect(rows.first).to_contain_text('Retrospective record; publication time unknown.')
        if width<720:
            scroll=page.get_by_role('region',name='Scored pick history, scroll horizontally for result and provenance')
            scroll.focus();page.keyboard.press('ArrowRight');page.wait_for_function('document.querySelector("#record-ledger .table-scroll").scrollLeft>0')
        page.locator('#record-all').click()
        page.locator('[data-record-view="prospective"]').focus();page.keyboard.press('Enter')
        expect(page.locator('#record-accuracy')).to_have_text('Not yet scored')
        expect(page.locator('.record-score')).to_contain_text('0 / 0');expect(page.locator('.record-chart')).to_have_count(0)
        expect(page.locator('.record-score')).not_to_contain_text('0.0%')
        page.reload();expect(page.locator('[data-record-view="prospective"]')).to_have_attribute('aria-pressed','true')
        page.go_back();expect(page.locator('.home-path .game')).to_have_count(15)
        page.go_forward();expect(page.locator('#record-accuracy')).to_have_text('Not yet scored')
        page.locator('[data-record-view="historical"]').click();page.select_option('#theme-choice','dark')
        page.evaluate('scrollTo(0,0)');page.screenshot(path=str(shots/f'track-record-{mode}-dark-{name}.png'))
        page.select_option('#theme-choice','light');page.evaluate('scrollTo(0,0)')
        page.screenshot(path=str(shots/f'track-record-{mode}-light-{name}.png'))
        finish(context,page,errors,'headline/calendar/all 377 ledger rows reconcile; keyboard, responsive scrolling, both themes, prospective empty, history',first_home_game=game)

        context,page,errors=fresh();page.route(path,lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Controlled track record outage"}'))
        page.goto(base+'/#record');expect(page.get_by_role('heading',name='Track record unavailable')).to_be_visible()
        expect(page.locator('#record-accuracy')).to_have_count(0)
        page.unroute(path);page.locator('#record-retry').focus();page.keyboard.press('Enter')
        expect(page.locator('#record-accuracy')).to_have_text('71.4%');expect(page.locator('[data-record-view="historical"]')).to_be_focused()
        finish(context,page,errors,'failure has no stale percentage; keyboard retry succeeds')

        context,page,errors=fresh();pending=[];page.route(path,lambda route:pending.append(route))
        page.goto(base+'/#record');expect(page.get_by_text('Loading saved track record…',exact=True)).to_be_visible()
        deadline=monotonic()+5
        while not pending and monotonic()<deadline:page.wait_for_timeout(10)
        assert len(pending)==1
        page.locator('.brand').click();expect(page.locator('.home-path .game')).to_have_count(15)
        pending[0].continue_();page.wait_for_load_state('networkidle');expect(page.locator('#record-accuracy')).to_have_count(0)
        expect(page.locator('.home-path .game')).to_have_count(15)
        finish(context,page,errors,'interrupted record load cannot replace bracket home')

        context,page,errors=fresh();empty=copy.deepcopy(data)
        for key in ['historical','prospective']:
            empty[key].update(records=[],points=[],totals=dict(correct=0,settled=0,accuracy_pct=None))
        page.route(path,lambda route:route.fulfill(content_type='application/json',body=json.dumps(empty)))
        page.goto(base+'/#record');expect(page.locator('#record-accuracy')).to_have_text('Not yet scored')
        expect(page.locator('.record-chart')).to_have_count(0);expect(page.locator('#record-ledger')).to_have_count(0)
        finish(context,page,errors,'zero eligible games display unscored without fabricated chart')
    (shots/f'track-record-{mode}-report.json').write_text(json.dumps(report,indent=2)+'\n')
