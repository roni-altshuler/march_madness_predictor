"""Bracket-first home: saved picks, one-action insights and interrupted loads."""
import json
from time import monotonic
from playwright.sync_api import expect


def assert_bracket_home(browser,shots,base,static):
    report=[];mode='static' if static else 'api'
    simulation_path='**/data/tables/2026.json' if static else '**/api/simulate?*'
    season_path='**/data/seasons/2026.json' if static else '**/api/season?*'
    for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
        def fresh():
            context=browser.new_context(viewport=dict(width=width,height=height),reduced_motion='reduce')
            page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            return context,page,errors
        def wait_pending(page,pending):
            deadline=monotonic()+5
            while not pending and monotonic()<deadline:page.wait_for_timeout(10)
            assert len(pending)==1
        def loaded(page):
            expect(page.locator('.home-path .game')).to_have_count(15)
            expect(page.locator('#home-bracket')).not_to_have_attribute('aria-busy','true')
        def finish(context,page,errors,case,**data):
            assert not errors,errors
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            report.append(dict(viewport=name,case=case,page_errors=errors,**data));context.close()

        context,page,errors=fresh();page.goto(base);loaded(page)
        expect(page.get_by_role('heading',name='2026 bracket',exact=True)).to_be_visible()
        expect(page.locator('nav a[href="#home"]')).to_have_attribute('aria-current','page')
        expect(page.locator('.home-context')).to_contain_text('Historical 2026 · 64 teams after First Four · trained through 2025')
        expect(page.locator('.home-method')).not_to_have_attribute('open','')
        # Compare displayed numbers with the real saved model, not a made-up forecast.
        if static:
            table=page.request.get(base+'/data/tables/2026.json').json()
            expected=table['seed']['seed']['probabilities'][0][15]
            simulation=page.evaluate("async()=>{const {request}=await import('./static_api.js');return request('/api/simulate?year=2026&rng=2027')}")
        else:
            expected=page.request.get(base+'/api/predict?a=1&b=16&year=2026&model=seed').json()['p_a']
            simulation=page.request.get(base+'/api/simulate?year=2026&rng=2027').json()
        expect(page.locator('.home-path .game-prob').first).to_have_text(f'{100*expected:.1f}%')
        leaders=sorted(simulation['odds'],key=lambda row:-row['champion'])[:4]
        expect(page.locator('.home-chances li strong')).to_have_text([f"{100*row['champion']:.1f}%" for row in leaders])
        expect(page.locator('.home-chances li a')).to_have_text([row['name'] for row in leaders])
        page.screenshot(path=str(shots/f'bracket-home-{mode}-{name}.png'))
        first=page.locator('.home-path .game:visible').first;position=first.bounding_box()['y']
        assert position<height-80,position
        first.focus();page.keyboard.press('Enter');expect(page.locator('dialog')).to_be_visible()
        expect(page.locator('dialog')).to_contain_text('MODEL PICK')
        expect(page.locator('dialog .probability')).to_have_text([f'{100*expected:.1f}%',f'{100*(1-expected):.1f}%'])
        expect(page.locator('.game-stats')).not_to_have_attribute('open','')
        page.locator('.game-stats summary').focus();page.keyboard.press('Enter')
        expect(page.get_by_text('Team comparison · form frozen March 1, 00:00 UTC',exact=True)).to_be_visible()
        page.keyboard.press('Enter');expect(page.locator('.game-stats')).not_to_have_attribute('open','')
        page.locator('dialog').screenshot(path=str(shots/f'bracket-home-game-{mode}-{name}.png'))
        page.keyboard.press('Escape');expect(page.locator('dialog')).not_to_be_visible()
        expect(page.locator('[data-game="0-0"]')).to_be_focused()
        page.go_back();loaded(page)
        for _ in range(3):
            button=page.locator('[data-home-region="1"]');button.focus();page.keyboard.press('Enter')
            expect(page.locator('[data-home-region="1"]')).to_be_focused()
        expect(page.locator('[data-home-region="1"]')).to_have_attribute('aria-pressed','true')
        if name=='mobile':page.select_option('#home-round','3')
        home_url=page.url
        card=page.locator('[data-home-game="2-0"]') if name=='desktop' else page.locator('.home-path .game:visible').first
        card.focus();page.keyboard.press('Enter');expect(page.locator('dialog')).to_be_visible()
        expect(page.locator('dialog .eyebrow')).to_contain_text('Sweet 16')
        page.go_back();loaded(page);expect(page).to_have_url(home_url)
        expect(page.locator('[data-home-region="1"]')).to_have_attribute('aria-pressed','true')
        if name=='mobile':expect(page.locator('#home-round')).to_have_value('3')
        page.locator('.home-chances li a').first.click();expect(page.locator('.team-profile h1')).to_have_text(leaders[0]['name'])
        page.go_back();loaded(page);expect(page).to_have_url(home_url)
        page.locator('.home-method summary').focus();page.keyboard.press('Enter')
        expect(page.locator('.home-method')).to_contain_text('not a live or 2027 forecast')
        expect(page.locator('.home-method')).to_contain_text('First Four games/losers are missing')
        page.get_by_role('link',name='Schedule & field import →').click()
        expect(page.get_by_role('heading',name='March 2027',exact=True)).to_be_visible()
        expect(page.locator('.game')).to_have_count(0);expect(page.locator('#field-file')).to_be_visible()
        page.go_back();loaded(page);expect(page).to_have_url(home_url)
        finish(context,page,errors,'saved probabilities, one-key game insight, optional stats, repeated controls, team/back and honest future field',firstGameY=position,homeToModelGameActions=1)

        context,page,errors=fresh();page.goto(base+'/#home?region=19&round=2.5');loaded(page)
        expect(page.locator('[data-home-region="0"]')).to_have_attribute('aria-pressed','true')
        for check_width in [320,390,720,721,768,1440]:
            page.set_viewport_size(dict(width=check_width,height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.locator('.home-path .game:visible').count()>0
        page.select_option('#theme-choice','dark');loaded(page)
        page.screenshot(path=str(shots/f'bracket-home-dark-{mode}-{name}.png'))
        finish(context,page,errors,'invalid state, six responsive widths, dark palette')

        context,page,errors=fresh()
        def missing(route):
            response=route.fetch();data=response.json();data['model']=None
            route.fulfill(response=response,json=data)
        page.route(season_path,missing);page.goto(base)
        expect(page.get_by_role('heading',name='Model bracket unavailable',exact=True)).to_be_visible()
        expect(page.locator('.home-path .game')).to_have_count(0)
        expect(page.get_by_role('link',name='Browse recorded results')).to_be_visible()
        finish(context,page,errors,'missing model stays empty; actual results remain reachable')

        context,page,errors=fresh();pending=[]
        page.route(simulation_path,lambda route:pending.append(route));page.goto(base)
        expect(page.locator('#home-bracket')).to_have_attribute('aria-busy','true')
        page.wait_for_function('document.querySelector("#home-bracket").textContent.includes("seed-model picks")')
        wait_pending(page,pending)
        pending[0].fulfill(status=503,content_type='application/json',body=json.dumps(dict(error='Controlled <home> outage')))
        expect(page.get_by_role('heading',name='Bracket couldn’t load',exact=True)).to_be_visible()
        expect(page.locator('#home-bracket [role="alert"]')).to_be_visible()
        expect(page.locator('#home-bracket [role="alert"] home')).to_have_count(0)
        page.locator('#home-bracket').screenshot(path=str(shots/f'bracket-home-error-{mode}-{name}.png'))
        page.unroute(simulation_path);page.locator('#home-retry').focus();page.keyboard.press('Enter');loaded(page)
        expect(page.locator('[data-home-region="0"]')).to_be_focused()
        finish(context,page,errors,'current error and keyboard retry restore usable bracket')

        for stage,path in [('season',season_path),('simulation',simulation_path)]:
            for failure in [False,True]:
                context,page,errors=fresh();pending=[];page.route(path,lambda route:pending.append(route));page.goto(base)
                wait_pending(page,pending)
                old=page.locator('#home-bracket').element_handle();markup=old.inner_html();busy=old.get_attribute('aria-busy')
                page.locator('nav a[href="#about"]').click();expect(page.get_by_role('heading',name='Know the data')).to_be_visible()
                content=page.locator('main').inner_html()
                if failure:pending[0].fulfill(status=503,content_type='application/json',body=json.dumps(dict(error='Controlled stale home failure')))
                else:pending[0].continue_()
                page.wait_for_load_state('networkidle')
                page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                assert page.locator('main').inner_html()==content
                assert old.inner_html()==markup and old.get_attribute('aria-busy')==busy and old.evaluate('(element)=>!element.isConnected')
                page.unroute(path);page.go_back();loaded(page)
                finish(context,page,errors,f'departed {stage} '+('failure' if failure else 'success')+' stays ignored; back recovers')
    (shots/f'bracket-home-{mode}-report.json').write_text(json.dumps(report,indent=2)+'\n')
