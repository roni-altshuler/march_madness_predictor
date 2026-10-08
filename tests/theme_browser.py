"""Continuous browser journeys: shared palettes, saved choice and system changes."""
import json
from playwright.sync_api import expect


def assert_palette(page, selector='main'):
    results = page.locator(selector).evaluate_all('''elements => elements.map(element => {
      const root=getComputedStyle(document.documentElement), style=getComputedStyle(element);
      const keys=['--bg','--surface','--surface2','--text','--muted','--blue','--accent','--green','--danger','--button-text'];
      return {scheme:style.colorScheme,rootScheme:root.colorScheme,
        same:keys.every(key=>style.getPropertyValue(key)===root.getPropertyValue(key)),
        font:style.fontFamily,bodyFont:getComputedStyle(document.body).fontFamily};
    })''')
    assert results
    for result in results:
        assert result['same'] and result['scheme'] == result['rootScheme'], result
        if selector != '.loading':  # Loading/numeric readouts intentionally use March Lab's mono face.
            assert result['font'] == result['bodyFont'], result
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def assert_contrast(page, selector, pseudo=None, boundary=False):
    ratios = page.locator(selector).evaluate_all(r'''(elements,options) => {
      const rgba=s=>s.match(/[\d.]+/g).map(Number);
      const light=rgb=>rgb.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4})
        .reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
      return elements.filter(e=>e.getClientRects().length && !e.disabled).map(e=>{
        let node=e,bg;
        while(node){const value=rgba(getComputedStyle(node).backgroundColor);if(value.length===3||value[3]===1){bg=value;break}node=node.parentElement}
        bg=bg||[255,255,255];const style=getComputedStyle(e,options.pseudo);
        const fg=rgba(options.boundary?style.borderTopColor:style.color),a=light(fg),b=light(bg);
        return {text:e.textContent.trim().slice(0,70),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
      });
    }''',dict(pseudo=pseudo,boundary=boundary))
    assert ratios and all(item['ratio'] >= (3 if boundary else 4.5) for item in ratios), ratios
    return min(item['ratio'] for item in ratios)


def assert_profile_control_frame(page):
    frame=page.evaluate('''() => new Promise(resolve=>requestAnimationFrame(()=>{
      const control=getComputedStyle(document.querySelector('#profile-year')),body=getComputedStyle(document.body);
      resolve({background:control.backgroundColor,bodyBackground:body.backgroundColor,
               text:control.color,bodyText:body.color});
    }))''')
    assert frame['background']==frame['bodyBackground'] and frame['text']==frame['bodyText'],frame


def assert_theme_journeys(browser, shots, base, static):
    report=[]
    summary_path='**/data/summary.json' if static else '**/api/summary'
    for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
        for theme in ['light','dark']:
            preference='dark' if theme=='light' else 'light'
            context=browser.new_context(viewport={'width':width,'height':height},color_scheme=preference)
            context.add_init_script(f'''if(!localStorage.getItem('marchlab.theme'))localStorage.setItem('marchlab.theme',{json.dumps(theme)});
              requestAnimationFrame(()=>window.firstThemeFrame={{theme:document.documentElement.dataset.theme,
                background:getComputedStyle(document.body).backgroundColor,
                content_opacity:getComputedStyle(document.querySelector('main')).opacity}});''')
            page=context.new_page();errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            pending=[];page.route(summary_path,lambda route:pending.append(route))
            page.goto(base+'/',wait_until='domcontentloaded')
            expect(page.locator('#theme-choice')).to_have_value(theme)
            expect(page.locator('main .loading')).to_be_visible()
            assert_palette(page,'.loading')
            page.wait_for_function('window.firstThemeFrame !== undefined')
            frame=page.evaluate('window.firstThemeFrame')
            expected_bg='rgb(234, 230, 220)' if theme=='light' else 'rgb(8, 11, 18)'
            assert frame == dict(theme=theme,background=expected_bg,content_opacity='1'),frame
            assert_contrast(page,'.loading')
            if name=='mobile': page.screenshot(path=str(shots/f'theme-loading-{theme}-mobile.png'))
            assert len(pending)==1
            pending[0].continue_();page.unroute(summary_path)
            expect(page.get_by_role('heading',name='March 2027',exact=True)).to_be_visible()
            assert_palette(page,'.hero')
            minimum=assert_contrast(page,'h1,.hero .muted,.hero .button,nav a')
            for check_width in [768,390,320,width]:
                page.set_viewport_size({'width':check_width,'height':height})
                assert_palette(page,'.hero')
            page.screenshot(path=str(shots/f'theme-home-{theme}-{name}.png'))

            page.get_by_role('link',name='Explore the historical bracket',exact=True).click()
            expect(page.locator('.game')).to_have_count(15)
            assert_palette(page,'.bracket-scroll')
            minimum=min(minimum,assert_contrast(page,'.won,.lost,.game-prob,.bracket-key'))
            minimum=min(minimum,assert_contrast(page,'.won .team-name','::after'))
            boundary_minimum=assert_contrast(page,'#theme-choice,.game',boundary=True)
            if theme=='light': page.screenshot(path=str(shots/f'theme-bracket-light-{name}.png'),full_page=True)
            card=page.locator('[data-game="2026-r1-0"]')
            card.focus();page.keyboard.press('Enter')
            expect(page.locator('dialog')).to_be_visible();assert_palette(page,'dialog')
            minimum=min(minimum,assert_contrast(page,'dialog .note,dialog a,dialog .probability'))
            page.locator('dialog').get_by_role('link',name='Duke',exact=True).focus();page.keyboard.press('Enter')
            expect(page.get_by_role('heading',name='Before the 2026 tournament')).to_be_visible()
            assert_palette(page,'.team-profile');assert_palette(page,'#team-scouting')
            minimum=min(minimum,assert_contrast(page,'.team-profile h1,.team-profile .note,.team-profile a,.scout-totals strong'))
            page.evaluate('scrollTo(0,0)')
            page.screenshot(path=str(shots/f'theme-profile-{theme}-{name}.png'))
            # Changing the header control must update a previously light-only detail page.
            page.select_option('#theme-choice',preference)
            expect(page.locator('html')).to_have_attribute('data-theme',preference)
            assert_profile_control_frame(page)
            assert_palette(page,'.team-profile');assert_palette(page,'#team-scouting')
            page.reload();expect(page.locator('#theme-choice')).to_have_value(preference)
            expect(page.locator('#scout-window')).to_have_value('5')
            page.select_option('#theme-choice','system')
            page.emulate_media(color_scheme=theme)
            expect(page.locator('html')).to_have_attribute('data-theme',theme)
            assert_profile_control_frame(page)
            assert_palette(page,'.team-profile');assert_palette(page,'#team-scouting')
            page.emulate_media(color_scheme=preference)
            expect(page.locator('html')).to_have_attribute('data-theme',preference)
            page.select_option('#theme-choice',theme)
            page.locator('#scout-window').focus();page.keyboard.press('Home');page.keyboard.press('Enter')
            expect(page.locator('#scout-window')).to_have_value('3')
            expect(page.locator('#scout-window')).to_be_focused()
            route=page.url
            page.reload();expect(page.locator('#scout-window')).to_have_value('3')
            expect(page).to_have_url(route);expect(page.locator('#theme-choice')).to_have_value(theme)
            page.go_back();expect(page.locator('#archive-year')).to_have_value('2026');assert_palette(page,'.bracket-scroll')
            page.go_forward();expect(page.locator('#scout-window')).to_have_value('3');assert_palette(page,'.team-profile')
            page.select_option('#profile-year','2006')
            expect(page.locator('#team-scouting')).to_contain_text('No earlier appearances in this identity')
            assert_palette(page,'.scout-empty')
            if name=='mobile':page.locator('#team-scouting').screenshot(path=str(shots/f'theme-empty-{theme}-mobile.png'))

            page.locator('nav').get_by_role('link',name='Matchup lab').click()
            expect(page.locator('.forecast-card')).to_have_count(3)
            assert_palette(page,'#matchup-comparison');assert_palette(page,'.forecast-primary')
            minimum=min(minimum,assert_contrast(page,'.forecast-card .note,.forecast-pair strong,.compare-primary-label'))
            page.locator('#matchup-comparison').screenshot(path=str(shots/f'theme-comparison-{theme}-{name}.png'))
            page.select_option('#compare-year','2020')
            expect(page.locator('#matchup-comparison')).to_contain_text('2020 · no recorded matchups')
            assert_palette(page,'.cancelled-season')
            minimum=min(minimum,assert_contrast(page,'.cancelled-season .tag,.cancelled-season .muted'))
            page.locator('nav').get_by_role('link',name='Model evidence').click()
            expect(page.locator('.coverage-card')).to_have_count(3)
            assert_palette(page,'#season-insights')
            minimum=min(minimum,assert_contrast(page,'.coverage-card p,.coverage-card strong,.insight-footnote'))
            page.select_option('#insight-year','2020')
            expect(page.locator('#season-insights')).to_contain_text('2020 · no tournament played')
            assert_palette(page,'.cancelled-season')
            page.locator('nav').get_by_role('link',name='Data & method').click()
            expect(page.get_by_role('heading',name='Know the data')).to_be_visible()
            assert_palette(page,'.panel')
            minimum=min(minimum,assert_contrast(page,'.panel .muted,.panel .note'))

            page.goto(base+'/#team?profile=missing&from=2026')
            expect(page.get_by_role('heading',name='Team history unavailable')).to_be_visible()
            assert_palette(page,'.profile-empty')
            minimum=min(minimum,assert_contrast(page,'.profile-empty p,.profile-empty button'))
            if name=='mobile':
                page.evaluate('scrollTo(0,0)')
                page.screenshot(path=str(shots/f'theme-error-{theme}-mobile.png'))
            page.go_back();expect(page.get_by_role('heading',name='Know the data')).to_be_visible()
            page.locator('.brand').click();expect(page.get_by_role('heading',name='March 2027',exact=True)).to_be_visible()
            expect(page.locator('#theme-choice')).to_have_value(theme);assert_palette(page,'.hero')
            page.emulate_media(color_scheme=theme)
            assert page.locator('html').get_attribute('data-theme')==theme
            page.emulate_media(color_scheme=preference)
            assert page.locator('html').get_attribute('data-theme')==theme
            page.select_option('#theme-choice','system')
            assert page.locator('html').get_attribute('data-theme')==preference
            page.emulate_media(color_scheme=theme)
            expect(page.locator('html')).to_have_attribute('data-theme',theme);assert_palette(page,'.hero')
            page.reload();expect(page.locator('#theme-choice')).to_have_value('system')
            expect(page.locator('html')).to_have_attribute('data-theme',theme)
            assert not errors,errors
            report.append(dict(viewport=name,theme=theme,opposite_system_preference=preference,
                               first_frame=frame,minimum_sampled_text_contrast=round(minimum,2),
                               minimum_sampled_control_border_contrast=round(boundary_minimum,2),page_errors=errors))
            context.close()

    # Storage restrictions/invalid values must not prevent navigation or system updates.
    for blocked in [False,True]:
        context=browser.new_context(color_scheme='light')
        context.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw Error('storage blocked')}})" if blocked else "localStorage.setItem('marchlab.theme','invalid')")
        page=context.new_page();page.goto(base+'/')
        expect(page.get_by_role('heading',name='March 2027',exact=True)).to_be_visible()
        expect(page.locator('#theme-choice')).to_have_value('system')
        page.select_option('#theme-choice','dark');assert_palette(page,'.hero')
        page.locator('nav').get_by_role('link',name='Historical bracket').click()
        expect(page.locator('.game')).to_have_count(15);expect(page.locator('html')).to_have_attribute('data-theme','dark')
        context.close()
    (shots/'theme-journey-report.json').write_text(json.dumps(report,indent=2)+'\n')
