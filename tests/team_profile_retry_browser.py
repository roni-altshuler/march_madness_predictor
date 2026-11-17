"""Keyboard focus ownership across real team-profile retry requests."""
import hashlib
import json
from playwright.sync_api import expect
from bracket_drilldown_browser import wait_pending


def assert_team_profile_retry(browser, shots, base, static):
    report=[]
    path=('**/data/teams/'+hashlib.sha256(b'espn:150').hexdigest()+'.json'
          if static else '**/api/team?profile=*')
    for viewport,width in [('mobile',390),('tablet',768),('desktop',1440)]:
        for outcome in ['failure','success','other-control-success','other-control-failure','back-success','back-failure','navigation']:
            context=browser.new_context(viewport={'width':width,'height':844})
            page=context.new_page();errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.route(path,lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Team history temporarily unavailable"}'))
            page.goto(base+'/#team?profile=espn%3A150&from=2026&appearance=2026')
            retry=page.locator('#profile-retry');expect(retry).to_be_visible()
            # A saved reading location from a previous Back journey must not
            # override newer retry or control focus when the response arrives.
            page.evaluate('history.replaceState({marchTeamReturn:{route:location.hash,href:document.querySelector(".profile-back").getAttribute("href")}},"",location.href)')
            page.unroute(path);pending=[]
            page.route(path,lambda route:pending.append(route))
            retry.focus();page.keyboard.press('Enter');wait_pending(page,pending,1)
            loading=page.locator('.team-profile [role="status"]')
            expect(loading).to_be_focused()
            expect(loading).to_contain_text('Loading recorded tournament appearances')
            if outcome.startswith('other-control'):
                page.locator('nav a[href="#about"]').focus()
            elif outcome.startswith('back'):
                page.keyboard.press('Shift+Tab')
                expect(page.locator('.profile-back')).to_be_focused()
            elif outcome=='navigation':
                page.locator('nav a[href="#about"]').focus();page.keyboard.press('Enter')
                expect(page.get_by_role('heading',name='Know the data',exact=True)).to_be_visible()
                page.evaluate('window.profileRetryNavigationFocus=document.activeElement')
            if outcome.endswith('failure'):
                pending[0].fulfill(status=503,content_type='application/json',body='{"error":"Team history temporarily unavailable"}')
                expect(retry).to_be_visible()
            else:
                pending[0].continue_()
                if outcome!='navigation':expect(page.locator('#profile-year')).to_have_value('2026')
            page.wait_for_load_state('networkidle')
            if outcome=='failure':expect(retry).to_be_focused()
            elif outcome=='success':expect(page.locator('#profile-year')).to_be_focused()
            elif outcome.startswith('other-control'):expect(page.locator('nav a[href="#about"]')).to_be_focused()
            elif outcome.startswith('back'):expect(page.locator('.profile-back')).to_be_focused()
            else:
                expect(page.get_by_role('heading',name='Know the data',exact=True)).to_be_visible()
                expect(page.locator('.team-profile')).to_have_count(0)
                assert page.evaluate('document.activeElement===window.profileRetryNavigationFocus')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors,errors
            if outcome in ['failure','success']:
                page.screenshot(path=str(shots/f'team-profile-retry-{outcome}-{"static" if static else "api"}-{viewport}.png'))
            report.append(dict(viewport=viewport,outcome=outcome,focused=page.evaluate('document.activeElement.tagName+"#"+document.activeElement.id'),page_errors=errors))
            context.close()
    (shots/f'team-profile-retry-{"static" if static else "api"}-report.json').write_text(json.dumps(report,indent=2)+'\n')
