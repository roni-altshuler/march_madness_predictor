"""Real-browser model path, provenance and interrupted request regressions."""
from pathlib import Path
import json
from playwright.sync_api import expect
from bracket_drilldown_browser import wait_pending
ROOT=Path(__file__).resolve().parents[1]


def assert_model_brackets(browser,shots,base,static):
    report=[];path='**/data/tables/2026.json' if static else '**/api/simulate?year=2026&*'
    for viewport,width in [('desktop',1440),('mobile',390)]:
        def fresh(route='#archive?year=2026&region=0&view=actual&round=3'):
            context=browser.new_context(viewport={'width':width,'height':1000 if width>720 else 844})
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/'+route)
            return context,page,errors
        context,page,errors=fresh();expect(page.locator('.game')).to_have_count(15)
        page.locator('#fill-bracket').focus();page.keyboard.press('Enter')
        expect(page.locator('[data-view="recommend"]')).to_have_attribute('aria-pressed','true',timeout=15000)
        expect(page.locator('[data-view="recommend"]')).to_be_focused()
        summary=page.locator('.model-bracket-summary');expect(summary).to_contain_text('Champion pick: Duke')
        expect(summary).to_contain_text('9.3%');expect(summary).to_contain_text('trained through 2025')
        expect(summary).to_contain_text('First Four games/losers are missing')
        rationale=page.locator('.model-bracket-rationale')
        assert not rationale.evaluate('(e)=>e.open')
        # The first game must fit without scrolling past context or controls.
        page.evaluate('scrollTo(0,0)')
        first_game=page.locator('.round-column.mobile-selected .game').first
        first_position=first_game.bounding_box()
        assert first_position['y']+first_position['height']<=page.viewport_size['height'],first_position
        assert rationale.evaluate('(e)=>Boolean(document.querySelector(".bracket-scroll").compareDocumentPosition(e)&Node.DOCUMENT_POSITION_FOLLOWING)')
        route=page.url;markup=page.locator('.bracket').inner_html()
        rationale.locator('summary').focus();page.keyboard.press('Enter')
        expect(rationale).to_contain_text('Input: selection-time seeds only.')
        expect(rationale).to_contain_text('Calibration through 2025.')
        expect(rationale).to_contain_text('does not optimize a scoring pool')
        assert rationale.evaluate('(e)=>e.open')
        page.keyboard.press('Enter');assert not rationale.evaluate('(e)=>e.open')
        assert page.url==route and page.locator('.bracket').inner_html()==markup
        diagnostic=page.locator('#season-content > details.panel');assert not diagnostic.evaluate('(e)=>e.open')
        panel_labels=[]
        expected_labels={
            'recommend':'The bracket above shows deterministic seed-baseline picks.',
            'sample':'The bracket above is one sampled random draw.',
            'actual':'The bracket above shows recorded actual results.',
        }
        for panel_mode,expected in expected_labels.items():
            control=page.locator(f'[data-view="{panel_mode}"]');control.focus();page.keyboard.press('Enter')
            panel=page.locator('#advancement-panel')
            if panel_mode=='recommend':
                panel.locator('summary').focus();page.keyboard.press('Enter')
                assert panel.evaluate('(element)=>element.open')
            note=panel.locator('p.note').first;expect(note).to_be_visible()
            expect(note).to_contain_text(expected)
            expect(note).to_contain_text('Conditional on the 64 main-bracket participants')
            if panel_mode=='recommend':
                expect(note).not_to_contain_text('recorded actual results')
                expect(note).to_contain_text('First Four games/losers are not bundled')
                expect(note).to_contain_text('seeds only, without roster updates, injuries or current form information')
                panel.evaluate('(element)=>element.scrollIntoView({block:"start"})')
                page.screenshot(path=str(shots/f'model-bracket-panel-{viewport}.png'))
            archive_note=page.locator('#season-content > p.note').first
            if panel_mode=='actual':expect(archive_note).to_contain_text('Verified scores and UTC dates appear in game details.')
            else:
                expect(archive_note).to_contain_text('recorded scores and dates are omitted')
                expect(archive_note).not_to_contain_text('Verified scores and UTC dates appear')
            panel_labels.append(dict(mode=panel_mode,text=note.inner_text(),archive_note=archive_note.inner_text()))
        page.locator('[data-view="recommend"]').click()
        count=0
        for region in range(5):
            button=page.locator(f'[data-region="{region}"]');button.focus();page.keyboard.press('Enter')
            expect(button).to_be_focused();count+=page.locator('.game').count()
        assert count==63
        if viewport=='mobile':page.select_option('#mobile-round','1')
        card=page.locator('.round-column[data-column="1"] .game')
        card.focus();page.keyboard.press('Enter');expect(page.locator('dialog .tag')).to_have_text('MODEL PICK')
        expect(page.locator('#detail-title')).to_have_text('Duke vs Arizona')
        expect(page.locator('dialog')).to_contain_text('not recorded winners')
        assert page.locator('dialog').get_by_text('Final:',exact=False).count()==0
        page.locator('#detail-title').get_by_role('link',name='Duke',exact=True).focus();page.keyboard.press('Enter')
        expect(page.locator('#profile-year')).to_have_value('2026');assert 'from_view=recommend' in page.url
        page.locator('.profile-back').focus();page.keyboard.press('Enter');expect(card).to_be_focused()
        expect(page.locator('[data-view="recommend"]')).to_have_attribute('aria-pressed','true')
        page.go_back();expect(page.locator('#profile-year')).to_have_value('2026')
        page.go_forward();expect(card).to_be_focused()
        model_markup=page.locator('.bracket').inner_html()
        page.evaluate('Date.now=()=>42');page.locator('[data-view="sample"]').click();page.locator('#draw-bracket').click()
        expect(page.locator('#draw-bracket')).to_be_enabled(timeout=15000)
        expect(page.locator('[data-view="sample"]')).to_have_attribute('aria-pressed','true',timeout=15000)
        expect(page.locator('.model-bracket-summary')).to_have_count(0)
        random_markup=page.locator('.bracket').inner_html()
        page.locator('[data-view="recommend"]').click();assert page.locator('.bracket').inner_html()==model_markup
        page.locator('[data-view="sample"]').click();assert page.locator('.bracket').inner_html()==random_markup
        page.locator('[data-view="actual"]').click();expect(page.locator('.bracket-key')).to_contain_text('Actual winner')
        page.locator('#fill-bracket').click();page.reload()
        expect(page.locator('[data-view="recommend"]')).to_have_attribute('aria-pressed','true',timeout=15000)
        expect(summary).to_contain_text('Champion pick: Duke')
        page.locator('[data-region="0"]').click()
        page.set_viewport_size({'width':390,'height':844});page.select_option('#mobile-round','0')
        layout=[]
        for check_width in [320,390,720,721,768,1440]:
            page.set_viewport_size({'width':check_width,'height':844});page.evaluate('scrollTo(0,0)')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            first=page.locator('.round-column.mobile-selected .game').first.bounding_box()
            assert first['y']+first['height']<=844,dict(width=check_width,first=first)
            for control in page.locator('.bracket-controls button').all():
                box=control.bounding_box();assert box['height']>=44,box
            layout.append(dict(width=check_width,first_game=first))
        page.set_viewport_size({'width':width,'height':1000 if width>720 else 844})
        page.select_option('#theme-choice','dark');expect(page.locator('html')).to_have_attribute('data-theme','dark')
        page.evaluate('scrollTo(0,0)');page.screenshot(path=str(shots/f'model-bracket-dark-{viewport}.png'))
        page.select_option('#theme-choice','light');page.locator('[data-region="0"]').click()
        if viewport=='mobile':page.select_option('#mobile-round','2')
        page.evaluate('scrollTo(0,0)');page.screenshot(path=str(shots/f'model-bracket-light-{viewport}.png'))
        page.select_option('#archive-year','1985');expect(page.locator('.game')).to_have_count(15)
        expect(page.locator('#fill-bracket')).to_be_disabled();expect(summary).to_have_count(0)
        assert page.locator('.game-prob').all_text_contents()==['—']*15
        expect(page.locator('#bracket-status')).to_contain_text('no prior-trained snapshot')
        page.select_option('#archive-year','2021');expect(page.locator('.game')).to_have_count(15)
        page.locator('#fill-bracket').click();expect(page.locator('[data-view="recommend"]')).to_have_attribute('aria-pressed','true',timeout=15000)
        for historical_mode in ['recommend','sample','actual']:
            page.locator(f'[data-view="{historical_mode}"]').click()
            footer=page.locator('#season-content > p.note').first
            if historical_mode=='actual':expect(footer).to_contain_text('Oregon–VCU was a no-contest')
            else:expect(footer).not_to_contain_text('the advancement is shown')
        assert not errors,errors
        report.append(dict(viewport=viewport,case='63 coherent main-bracket picks, prior snapshot, collapsed details, actual/random distinction, profile/history/reload, themes and missing model',champion='Duke',probability='9.3%',trained_through=2025,advancement_panel_modes=panel_labels,first_game_positions=layout,page_errors=errors));context.close()

        # Keep latest region/round focus during model completion and reject old-year work.
        for leave in [False,True]:
            context,page,errors=fresh();expect(page.locator('.game')).to_have_count(15)
            pending=[];page.route(path,lambda route:pending.append(route))
            page.locator('#fill-bracket').click();wait_pending(page,pending,1)
            expect(page.locator('#bracket-status')).to_contain_text('Building the model-picked path')
            expect(page.locator('.model-bracket-summary')).to_have_count(0)
            if leave:
                page.select_option('#archive-year','1985');expect(page.locator('.game')).to_have_count(15)
            else:
                button=page.locator('[data-region="1"]');button.focus();page.keyboard.press('Enter');expect(button).to_be_focused()
            pending[0].continue_();page.wait_for_load_state('networkidle')
            if leave:
                expect(page.locator('#archive-year')).to_have_value('1985');expect(page.locator('#fill-bracket')).to_be_disabled()
                expect(page.locator('.model-bracket-summary')).to_have_count(0)
            else:
                expect(page.locator('[data-view="recommend"]')).to_have_attribute('aria-pressed','true')
                expect(page.locator('[data-region="1"]')).to_be_focused();expect(page.locator('#mobile-round')).to_have_value('2')
                assert 'region=1&view=recommend&round=3' in page.url
            assert not errors,errors
            report.append(dict(viewport=viewport,case='held generation after '+('year change' if leave else 'region/round change'),page_errors=errors));context.close()

        context,page,errors=fresh();expect(page.locator('.game')).to_have_count(15)
        page.route(path,lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Controlled model-bracket outage"}'))
        page.locator('#fill-bracket').click();expect(page.locator('#bracket-status')).to_contain_text('Model bracket unavailable.')
        expect(page.locator('.model-bracket-summary')).to_have_count(0);expect(page.locator('#fill-bracket')).to_be_enabled()
        expect(page.locator('.bracket-key')).to_contain_text('Actual winner')
        page.unroute(path);page.locator('#retry-bracket').focus();page.keyboard.press('Enter')
        expect(page.locator('[data-view="recommend"]')).to_have_attribute('aria-pressed','true',timeout=15000)
        assert not errors,errors;report.append(dict(viewport=viewport,case='explicit generation error and retry without fabricated picks',page_errors=errors));context.close()

        for missing,message in [(2020,'cancelled'),(2027,'field is unknown'),(1940,'No declared bracket')]:
            context,page,errors=fresh(f'#archive?year={missing}&view=recommend')
            expect(page.get_by_role('heading',name='Model bracket unavailable')).to_be_visible()
            expect(page.locator('main')).to_contain_text(message)
            expect(page.locator('.game')).to_have_count(0)
            assert not errors,errors
            report.append(dict(viewport=viewport,case='explicit unavailable model link',year=missing,page_errors=errors));context.close()

        if not static:
            context,page,errors=fresh();expect(page.locator('.game')).to_have_count(15)
            page.locator('#fill-bracket').click();expect(page.locator('[data-view="recommend"]')).to_have_attribute('aria-pressed','true',timeout=15000)
            page.locator('[data-view="sample"]').click();pending=[];page.route(path,lambda route:pending.append(route))
            page.locator('#draw-bracket').click();wait_pending(page,pending,1)
            model=page.locator('[data-view="recommend"]');model.focus();page.keyboard.press('Enter')
            pending[0].continue_();expect(page.locator('#draw-bracket')).to_be_enabled(timeout=15000)
            expect(model).to_have_attribute('aria-pressed','true');expect(model).to_be_focused()
            expect(page.locator('.model-bracket-summary')).to_contain_text('Champion pick: Duke')
            assert 'view=recommend' in page.url and not errors,errors
            report.append(dict(viewport=viewport,case='new model view wins over pending random draw completion',page_errors=errors));context.close()

        # First Four is a structural fixture only; no fixture entrants are published.
        context,page,errors=fresh('#2027');expect(page.locator('#field-file')).to_be_visible()
        expect(page.get_by_text('FIELD NOT ANNOUNCED',exact=True)).to_be_visible()
        teams=json.loads((ROOT/'data/derived/archive.json').read_text())['2026']['teams']
        field=dict(season=2026,status='test_only_local_scenario',expected_teams=68,expected_opening_games=4,slots=[[dict(id=t['id'],name=t['name'],seed=t['seed'])] for t in teams])
        for i in [1,5,17,21]:
            team=dict(field['slots'][i][0]);team.update(id=f'test-only-opening-{i}',name=f'Test only opening {i}');field['slots'][i].append(team)
        def upload(value):page.set_input_files('#field-file',{'name':'structural-test-only.json','mimeType':'application/json','buffer':json.dumps(value).encode()})
        upload(dict(season=2027,status='unknown'));expect(page.locator('#import-status')).to_contain_text('field is unknown')
        expect(page.locator('#import-result .game')).to_have_count(0)
        upload(field);expect(page.locator('#import-status')).to_have_text('Validated 68 teams and 67 games.')
        imported=page.locator('#import-result');expect(imported).to_contain_text('Local field scenario')
        expect(imported).to_contain_text('trained through 2026');expect(imported).to_contain_text('timestamp are not verified')
        rationale=imported.locator('.model-bracket-rationale');assert not rationale.evaluate('(e)=>e.open')
        rationale.locator('summary').focus();page.keyboard.press('Enter')
        expect(rationale).to_contain_text('Input: supplied seeds; their as-of timestamps are unverified.')
        expect(rationale).not_to_contain_text('Input: selection-time seeds only.')
        opening=imported.get_by_text('Opening / First Four picks · 4 games',exact=True);opening.click()
        expect(imported.locator('[data-opening-game]')).to_have_count(4)
        assert imported.locator('.bracket').get_by_text('Test only opening',exact=False).count()==0
        imported.locator('[data-opening-game]').first.click();expect(page.locator('dialog .tag')).to_have_text('MODEL PICK')
        expect(page.locator('dialog')).to_contain_text('not a historical as-of forecast')
        expect(page.locator('#detail-model')).to_have_count(0);page.keyboard.press('Escape')
        imported.locator('[data-import-view="sample"]').click();expect(imported).to_contain_text('ONE RANDOM SAMPLE')
        imported.locator('[data-import-view="recommend"]').click();expect(imported).to_contain_text('Champion pick')
        assert not errors,errors
        report.append(dict(viewport=viewport,case='unknown-field rejection and four opening-pair dependencies in local current-model scenario',fixture_only=True,participants=68,picks=67,page_errors=errors));context.close()

        # A delayed import cannot populate a newly reopened home page.
        context,page,errors=fresh('#2027');expect(page.locator('#field-file')).to_be_visible()
        import_path='**/data/tables/2027.json' if static else '**/api/simulate'
        pending=[];page.route(import_path,lambda route:pending.append(route))
        page.set_input_files('#field-file',{'name':'structural-test-only.json','mimeType':'application/json','buffer':json.dumps(field).encode()});wait_pending(page,pending,1)
        page.locator('nav a[href="#about"]').click();expect(page.get_by_role('heading',name='Know the data')).to_be_visible()
        page.locator('.brand').click();expect(page.get_by_role('heading',name='2026 bracket',exact=True)).to_be_visible()
        page.locator('nav a[href="#2027"]').click();expect(page.locator('#field-file')).to_be_visible()
        pending[0].continue_();page.wait_for_load_state('networkidle')
        expect(page.locator('#import-result .game')).to_have_count(0);expect(page.locator('#import-status')).to_have_text('')
        assert not errors,errors
        report.append(dict(viewport=viewport,case='delayed import after leave and reopen cannot render in new owner',page_errors=errors));context.close()
    (shots/f'model-bracket-{"static" if static else "api"}-report.json').write_text(json.dumps(dict(mode='static' if static else 'api',cases=report),indent=2)+'\n')
