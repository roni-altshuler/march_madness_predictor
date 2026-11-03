"""Scoring/audit regressions use synthetic fixtures; none are published as data."""
import copy
import pytest
from madness.data import ROOT, read
from madness.model import metrics
from madness.server import load_state
from madness.track_record import build_track_record, calendar_points, counts


def fixture(entries):
    archive, predictions, historical = {}, [], {}
    for index, (year, date, p, winner) in enumerate(entries):
        season = archive.setdefault(str(year), dict(teams=[dict(id='a', name='A'), dict(id='b', name='B')], games=[]))
        game = dict(id=f'{year}-{index:02}', season=year, round=1, round_name='Fixture round', a='a', b='b',
                    winner=winner, status='played', date_utc=date)
        season['games'].append(game)
        predictions.append(dict(game_id=game['id'], season=year, round=1, p=p, y=int(winner=='a'),
                                train_through=year-1, calibration_through=year-1))
        historical[str(year)] = dict(seed=dict(train_seasons=[year-1], calibration_through=year-1))
    return archive, dict(seed=predictions), dict(holdout=[2021, 2026]), historical


def build(data, **kwargs):
    return build_track_record(*data, as_of='2026-10-03', **kwargs)


@pytest.mark.parametrize('winner,expected', [('a', 1), ('b', 0)])
def test_exact_ties_choose_bracket_order_and_never_half_credit(winner, expected):
    report = build(fixture([(2021, '2021-03-20T12:00Z', .5, winner)]))
    assert report['historical']['records'][0]['pick'] == 'a'
    assert report['historical']['totals'] == dict(correct=expected, settled=1, accuracy_pct=100*expected)
    assert metrics([dict(y=int(winner=='a'), p=.5)])['accuracy'] == .5


def test_sorting_equal_times_and_reversed_input_are_stable():
    data = fixture([(2021, '2021-03-21T00:00Z', .9, 'a'), (2021, '2021-03-19T20:00Z', .9, 'b'),
                    (2021, '2021-03-19T20:00Z', .9, 'a')])
    expected = build(data)
    data[1]['seed'].reverse();data[0]['2021']['games'].reverse()
    assert build(data) == expected
    assert [row['game_id'] for row in expected['historical']['records']] == ['2021-01', '2021-02', '2021-00']
    assert expected['historical']['points'][0]['cumulative']['settled'] == 3


def test_unequal_partial_weeks_pool_counts_not_percentages():
    data = fixture([(2021, '2021-03-17T12:00Z', .9, 'a')]+[(2021, '2021-03-23T12:00Z', .9, 'b')]*3)
    report = build(data)['historical'];a,b = report['points']
    assert a['weekly']['accuracy_pct'] == 100
    assert b['weekly']['accuracy_pct'] == 0
    assert b['cumulative'] == dict(correct=1, settled=4, accuracy_pct=25)
    assert b['week_start'] == '2021-03-22' and b['week_end'] == '2021-03-28'
    assert b['recent']['settled'] == 4


def test_fixed_last_20_window_and_tournament_reset():
    data = fixture([(2021, '2021-03-19T12:00Z', .9, 'a')]+[(2021, '2021-03-23T12:00Z', .9, 'b')]*20+
                   [(2022, '2022-03-19T12:00Z', .9, 'a')])
    points = build(data)['historical']['points']
    assert points[1]['recent'] == dict(correct=0, settled=20, accuracy_pct=0)
    assert points[-1]['recent'] == dict(correct=1, settled=1, accuracy_pct=100)
    assert points[-1]['cumulative']['settled'] == 22


def test_iso_week_year_rollover_is_separate_from_tournament_reset():
    rows = [dict(season=2021,date_utc='2021-12-31T12:00Z',correct=1),
            dict(season=2021,date_utc='2022-01-03T12:00Z',correct=0),
            dict(season=2022,date_utc='2022-01-04T12:00Z',correct=1)]
    points = calendar_points(rows)
    assert [p['week'] for p in points] == ['2021-W52', '2022-W01', '2022-W01']
    assert [p['recent']['settled'] for p in points] == [1,2,1]
    assert [p['cumulative']['settled'] for p in points] == [1,2,3]


def test_zero_data_is_unscored_and_not_zero_percent():
    report = build(fixture([]))
    assert report['historical']['totals'] == counts([]) == dict(correct=0,settled=0,accuracy_pct=None)
    assert report['historical']['points'] == []
    assert report['prospective']['totals']['accuracy_pct'] is None


@pytest.mark.parametrize('mutation,reason', [
    ('no_contest','unsettled_or_no_contest'),('date','unknown_or_future_event_time'),
    ('future','unknown_or_future_event_time'),('train','invalid_prior_training'),
    ('calibration','invalid_prior_calibration'),('result','result_mismatch'),('duplicate','duplicate_event')])
def test_backtest_exclusions_are_explicit(mutation, reason):
    data = fixture([(2021, '2021-03-19T12:00Z', .9, 'a')]);game=data[0]['2021']['games'][0];p=data[1]['seed'][0]
    if mutation=='no_contest':game['status']='no_contest'
    if mutation=='date':game['date_utc']=None
    if mutation=='future':game['date_utc']='2027-03-19T12:00Z'
    if mutation=='train':p['train_through']=2021
    if mutation=='calibration':p['calibration_through']=2021
    if mutation=='result':p['y']=0
    if mutation=='duplicate':data[1]['seed'].append(copy.deepcopy(p))
    record=build(data)['historical']
    assert record['totals']['settled']==0 and record['excluded'][reason]>0


def forecast(data):
    return dict(data[1]['seed'][0], model='seed', pick='b', issued_at='2021-03-18T12:00Z', published_at='2021-03-18T13:00Z')


def test_prospective_scores_declared_pick_and_requires_real_pre_event_times():
    data=fixture([(2021, '2021-03-19T12:00Z', .1, 'b')]);p=forecast(data)
    # Require the explicit published pick; never infer a historical publication.
    report=build(data,forecasts=[p])['prospective']
    assert report['totals']==dict(correct=1,settled=1,accuracy_pct=100)
    for key,value in [('issued_at',None),('published_at',None),('published_at','2021-03-19T12:00Z'),
                      ('published_at','2021-03-20T12:00Z'),('issued_at','2021-03-18'),
                      ('issued_at','2021-03-18T12:00'),('issued_at','2021-03-18T14:00Z')]:
        bad=dict(p,**{key:value})
        assert build(data,forecasts=[bad])['prospective']['totals']['accuracy_pct'] is None
    assert build(data,forecasts=[p,p])['prospective']['totals']['settled']==0
    for bad in [dict(p,pick='a'),dict(p,pick=None),dict(p,train_through=2021),dict(p,calibration_through=2021),
                dict(p,train_through=True),dict(p,calibration_through='unknown')]:
        assert build(data,forecasts=[bad])['prospective']['totals']['settled']==0


def test_bundled_holdout_reconciles_every_record_and_point():
    report=load_state()['track_record'];h=report['historical'];rows=h['records']
    assert h['totals']['correct']==269 and h['totals']['settled']==377
    assert h['totals']['accuracy_pct']==pytest.approx(100*269/377)
    assert len(rows)==len({r['game_id'] for r in rows})==377
    assert counts(rows)==h['totals']==h['points'][-1]['cumulative']
    assert sum(p['weekly']['correct'] for p in h['points'])==269
    assert sum(p['weekly']['settled'] for p in h['points'])==377
    assert h['coverage']==dict(archived_games=378,no_contests=1,eligible_games=377,
                               settled_results=377,missing_or_ineligible_picks=0,unavailable_results=0)
    assert all(r['train_through']<r['season'] and r['calibration_through']<r['season'] for r in rows)
    assert h['excluded']=={} and report['prospective']['records']==[]
    assert report['prospective']['totals']['accuracy_pct'] is None
    assert all(r['issued_at'] is None and r['published_at'] is None for r in rows)
    assert set(report['sources_sha256'])=={'artifacts/predictions.json','data/derived/archive.json',
          'artifacts/historical_models.json','artifacts/evaluation.json','artifacts/models.json'}


def test_each_tournament_reconciles_without_inheriting_other_seasons():
    report=load_state()['track_record'];h=report['historical']
    expected={2021:(43,62),2022:(42,63),2023:(44,63),2024:(44,63),2025:(50,63),2026:(46,63)}
    for year,(correct,settled) in expected.items():
        season=h['seasons'][str(year)]
        assert season['totals']==dict(correct=correct,settled=settled,accuracy_pct=100*correct/settled)
        assert season['points'][-1]['cumulative']==season['totals']
        assert all(p['season']==year for p in season['points'])
        assert season['coverage']['no_contests']==int(year==2021)
        assert season['coverage']['archived_games']==63
        assert season['coverage']['missing_or_ineligible_picks']==0
    assert sum(s['totals']['correct'] for s in h['seasons'].values())==269
    assert sum(s['totals']['settled'] for s in h['seasons'].values())==377
    published=report['prospective']['seasons']['2021']
    assert published['totals']==dict(correct=0,settled=0,accuracy_pct=None)
    assert published['coverage']['settled_results']==62
    assert published['coverage']['missing_or_ineligible_picks']==62


def test_coverage_separates_missing_invalid_unavailable_and_no_contest_games():
    data=fixture([(2021,f'2021-03-{19+i:02}T12:00Z',.9,'a') for i in range(6)])
    games=data[0]['2021']['games'];predictions=data[1]['seed']
    predictions.pop(1)  # A real settled result with no saved prediction.
    predictions[1]['train_through']=2021
    games[3]['date_utc']=None
    games[4]['status']='no_contest'
    games[5].update(status='scheduled',winner=None)
    record=build(data)['historical']
    assert record['totals']==dict(correct=1,settled=1,accuracy_pct=100)
    expected=dict(archived_games=6,no_contests=1,eligible_games=1,settled_results=3,
                  missing_or_ineligible_picks=2,unavailable_results=2)
    assert record['coverage']==record['seasons']['2021']['coverage']==expected
    predictions.append(copy.deepcopy(predictions[0]))
    record=build(data)['historical']
    assert record['totals']['settled']==0
    assert record['coverage']['missing_or_ineligible_picks']==3  # Unique games, not four rejected rows.
    assert record['coverage']['no_contests']==1 and record['coverage']['unavailable_results']==2


def test_empty_tournaments_remain_unscored_without_invented_results():
    report=build(fixture([]))
    for view in ['historical','prospective']:
        for season in report[view]['seasons'].values():
            assert season['totals']==dict(correct=0,settled=0,accuracy_pct=None)
            assert season['points']==[] and not any(season['coverage'].values())
