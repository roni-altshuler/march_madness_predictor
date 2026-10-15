"""Test-only latency controls; static success delegates unchanged saved-table calculations."""
import json
from urllib.parse import parse_qs,urlsplit

STATIC_WRAPPER='''
export async function request(path,options={}){
  const q=new URL(path,location.origin),gate=window.__seedGate;
  if(!gate||q.pathname!=='/api/predict'||q.searchParams.get('year')!=='2027')return originalRequest(path,options);
  const index=gate.holds.findIndex(h=>String(h.a)===q.searchParams.get('a')&&String(h.b)===q.searchParams.get('b')&&h.model===q.searchParams.get('model'));
  if(index<0)return originalRequest(path,options);
  gate.holds.splice(index,1);
  const computed=originalRequest(path,options);computed.catch(()=>{});
  return new Promise((resolve,reject)=>gate.pending.push({path,release:()=>computed.then(resolve,reject),fail:()=>reject(Error('Controlled <seed> outage'))}));
}
'''

class SeedRequestGate:
    def __init__(self,page,root,static,holds):
        self.page=page;self.static=static;self.holds=list(holds);self.pending=[]
        if static:
            page.add_init_script('window.__seedGate='+json.dumps(dict(holds=holds,pending=[]))+';')
            source=(root/'web/static_api.js').read_text()
            marker='export async function request(path,options={}){'
            assert source.count(marker)==1
            source=source.replace(marker,'async function originalRequest(path,options={}){')+STATIC_WRAPPER
            page.route('**/static_api.js',lambda route:route.fulfill(status=200,content_type='text/javascript',body=source))
        else:
            def handler(route):
                q=parse_qs(urlsplit(route.request.url).query)
                for i,h in enumerate(self.holds):
                    if q.get('year')==['2027'] and all(q.get(k)==[str(h[k])] for k in ['a','b','model']):
                        self.holds.pop(i);self.pending.append(route);return
                route.continue_()
            page.route('**/api/predict?*',handler)

    def add(self,*holds):
        if self.static:self.page.evaluate('(holds)=>window.__seedGate.holds.push(...holds)',list(holds))
        else:self.holds.extend(holds)

    def wait(self,count):
        if self.static:self.page.wait_for_function('(count)=>window.__seedGate.pending.length===count',arg=count)
        else:
            from time import monotonic
            deadline=monotonic()+5
            while len(self.pending)<count and monotonic()<deadline:self.page.wait_for_timeout(10)
            assert len(self.pending)==count

    def release(self,index,failure=False):
        if self.static:self.page.evaluate('([i,fail])=>window.__seedGate.pending[i][fail?"fail":"release"]()',[index,failure])
        else:
            route=self.pending[index]
            with self.page.expect_response(lambda response:response.url==route.request.url) as response:
                if failure:route.fulfill(status=503,content_type='application/json',body=json.dumps(dict(error='Controlled <seed> outage')))
                else:route.continue_()
            response.value.body()

    def settle(self):
        self.page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')

from pathlib import Path
from playwright.sync_api import expect
ROOT=Path(__file__).resolve().parents[1]


def assert_seed_matchup_requests(browser,shots,base,static):
    report=[];mode='static' if static else 'api'
    for viewport,width,height in [('desktop',1440,1000),('mobile',390,844)]:
        def fresh(*holds):
            context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            gate=SeedRequestGate(page,ROOT,static,list(holds));page.goto(base+'/#matchup')
            return context,page,gate,errors
        def hold(a=5,b=12,model='seed'):return dict(a=a,b=b,model=model)
        def submit(page,a,b,model='seed'):
            page.fill('#seed-a',str(a));page.fill('#seed-b',str(b));page.select_option('#matchup-model',model)
            page.get_by_role('button',name='Compare seeds',exact=True).focus();page.keyboard.press('Enter')
        def expected(page,a,b,kind):
            if static:
                response=page.request.get(base+'/data/tables/2027.json');assert response.ok
                p=response.json()['seed'][kind]['probabilities'][a-1][b-1];values=[p,1-p]
            else:
                response=page.request.get(base+f'/api/predict?a={a}&b={b}&model={kind}&year=2027');assert response.ok
                data=response.json();values=[data['p_a'],data['p_b']]
            return [f'{p*100:.1f}%' for p in values]
        def assert_result(page,a,b,kind='seed'):
            target=page.locator('#matchup-result');label='Seed baseline · primary' if kind=='seed' else 'Seed curve · challenger'
            expect(target.locator('.probability')).to_have_text(expected(page,a,b,kind))
            expect(target).to_contain_text(f'TEAM A · SEED {a}');expect(target).to_contain_text(f'TEAM B · SEED {b}')
            expect(target.locator('p.note').first).to_contain_text(label)
            expect(target).to_contain_text('fitted through 2026 · no announced 2027 teams.')
            assert target.get_attribute('aria-busy') is None
        def capture(page,state):
            page.locator('#matchup-form').locator('..').screenshot(path=str(shots/f'seed-matchup-{mode}-{state}-{viewport}.png'))
        def finish(context,page,errors,case,**extra):
            page.wait_for_load_state('networkidle')
            assert not errors,errors;assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            report.append(dict(viewport=viewport,case=case,inputs=[page.input_value('#seed-a'),page.input_value('#seed-b')],model=page.input_value('#matchup-model'),result=page.locator('#matchup-result').inner_text(),page_errors=errors,**extra));context.close()

        # A held initial 5-v-12 response must not replace the newer 8-v-8 result.
        for failure in [False,True]:
            context,page,gate,errors=fresh(hold());gate.wait(1)
            submit(page,8,8);assert_result(page,8,8)
            before=page.locator('#matchup-result').inner_html();gate.release(0,failure);gate.settle()
            assert page.locator('#matchup-result').inner_html()==before;assert_result(page,8,8)
            expect(page.get_by_role('button',name='Compare seeds',exact=True)).to_be_focused()
            capture(page,'stale-failure' if failure else 'stale-success')
            finish(context,page,errors,'stale failure ignored' if failure else 'stale success ignored')

        # Old success/failure cannot clear the current request's loading state.
        for failure in [False,True]:
            context,page,gate,errors=fresh(hold(),hold(8,8));gate.wait(1)
            submit(page,8,8);gate.wait(2);target=page.locator('#matchup-result')
            expect(target).to_have_attribute('aria-busy','true');loading=target.inner_html()
            gate.release(0,failure);gate.settle()
            assert target.inner_html()==loading;expect(target).to_have_attribute('aria-busy','true')
            expect(target.locator('.probability')).to_have_count(0)
            gate.release(1);assert_result(page,8,8)
            finish(context,page,errors,'stale '+('failure' if failure else 'success')+' preserves newer loading')

        # The selected challenger is labeled honestly and remains the latest model.
        context,page,gate,errors=fresh(hold());gate.wait(1)
        submit(page,5,12,'seed_curve');assert_result(page,5,12,'seed_curve')
        before=page.locator('#matchup-result').inner_html();gate.release(0);gate.settle()
        assert page.locator('#matchup-result').inner_html()==before;capture(page,'curve')
        finish(context,page,errors,'latest model switch preserves curve probabilities and label')

        # Unsubmitted edits must not relabel an already submitted request.
        context,page,gate,errors=fresh(hold());gate.wait(1)
        page.fill('#seed-a','8');page.fill('#seed-b','8');page.select_option('#matchup-model','seed_curve')
        gate.release(0);assert_result(page,5,12,'seed')
        finish(context,page,errors,'request inputs/model label are snapshots, independent of later edits')

        # Repeated real keyboard submissions can complete in reverse order.
        context,page,gate,errors=fresh();assert_result(page,5,12)
        gate.add(hold(),hold(8,8),hold(1,16,'seed_curve'))
        submit(page,5,12);submit(page,8,8);submit(page,1,16,'seed_curve');gate.wait(3)
        gate.release(2);assert_result(page,1,16,'seed_curve');before=page.locator('#matchup-result').inner_html()
        gate.release(1,True);gate.release(0);gate.settle()
        assert page.locator('#matchup-result').inner_html()==before
        expect(page.get_by_role('button',name='Compare seeds',exact=True)).to_be_focused()
        capture(page,'keyboard');finish(context,page,errors,'three repeated keyboard submissions; reverse success/failure completion')

        # Retry stays inside this form and keeps its seeds and selected model.
        context,page,gate,errors=fresh();assert_result(page,5,12)
        gate.add(hold(5,12,'seed_curve'));submit(page,5,12,'seed_curve');gate.wait(1);gate.release(0,True)
        target=page.locator('#matchup-result');expect(target.get_by_role('alert')).to_contain_text('Seed curve · challenger: scenario unavailable. Controlled <seed> outage')
        expect(target.locator('.probability')).to_have_count(0);assert target.get_attribute('aria-busy') is None
        capture(page,'current-error');route=page.url
        page.locator('#retry-matchup').focus();page.keyboard.press('Enter');assert_result(page,5,12,'seed_curve')
        expect(page.get_by_role('button',name='Compare seeds',exact=True)).to_be_focused()
        assert page.url==route;expect(page.locator('#matchup-model')).to_have_value('seed_curve')
        expect(page.locator('#seed-a')).to_have_value('5');expect(page.locator('#seed-b')).to_have_value('12')
        finish(context,page,errors,'current failure and keyboard retry preserve form/model')

        # Departed containers remain untouched even after returning to the same route.
        for failure in [False,True]:
            context,page,gate,errors=fresh(hold());gate.wait(1)
            old=page.locator('#matchup-result').element_handle();old_markup=old.inner_html();old_busy=old.get_attribute('aria-busy')
            page.locator('nav a[href="#archive"]').click();expect(page.locator('.game')).to_have_count(15)
            page.go_back();assert_result(page,5,12);submit(page,8,8);assert_result(page,8,8)
            expect(page.locator('#compare-status')).to_have_text('2026 saved matchup comparison loaded.')
            before=page.locator('main').inner_html();route=page.url;gate.release(0,failure);gate.settle()
            assert page.locator('main').inner_html()==before and page.url==route
            assert old.inner_html()==old_markup and old.get_attribute('aria-busy')==old_busy
            assert old.evaluate('(e)=>!e.isConnected')
            finish(context,page,errors,'navigation away/back rejects old '+('failure' if failure else 'success')+' and leaves disconnected container untouched')

        context,page,gate,errors=fresh();assert_result(page,5,12)
        for check_width in [320,390,720,721,768,1440]:
            page.set_viewport_size({'width':check_width,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.set_viewport_size({'width':width,'height':height});page.select_option('#theme-choice','dark');assert_result(page,5,12)
        finish(context,page,errors,'six responsive widths and dark palette preserve scenario labels')
    (shots/f'seed-matchup-{mode}-report.json').write_text(json.dumps(dict(mode=mode,static_latency='test-only per-prediction delay delegating unchanged saved-table calculations' if static else None,cases=report),indent=2)+'\n')
