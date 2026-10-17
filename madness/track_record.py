"""Integer game-pick scoring from saved records, never from fractional metrics()."""
from collections import Counter
from datetime import datetime, time, timezone, timedelta
from itertools import groupby
import math

RECENT_GAMES = 20


def timestamp(value):
    """Require a known, timezone-aware event/publication time, not a date guess."""
    if not isinstance(value, str) or 'T' not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.utcoffset() is not None else None
    except ValueError:
        return None


def counts(rows):
    settled = len(rows)
    correct = sum(row['correct'] for row in rows)
    return dict(correct=correct, settled=settled,
                accuracy_pct=100 * correct / settled if settled else None)


def calendar_points(rows):
    """Whole UTC ISO weeks; pooled integer counts, not means of percentages."""
    points, cumulative, recent, prior_season = [], [], [], None
    def week(row):
        return row['season'], timestamp(row['date_utc']).isocalendar()[:2]
    for (season, (iso_year, iso_week)), batch in groupby(rows, key=week):
        batch = list(batch)
        if season != prior_season:
            recent = []
        prior_season = season
        cumulative.extend(batch)
        recent = (recent + batch)[-RECENT_GAMES:]
        start = datetime.fromisocalendar(iso_year, iso_week, 1).date()
        points.append(dict(season=season, week=f'{iso_year}-W{iso_week:02}',
                           week_start=str(start), week_end=str(start + timedelta(days=6)),
                           date_utc=batch[-1]['date_utc'], weekly=counts(batch),
                           cumulative=counts(cumulative), recent=counts(recent),
                           recent_start=recent[0]['date_utc'], recent_end=recent[-1]['date_utc']))
    return points


def build_track_record(archive, predictions, evaluation, historical, as_of, forecasts=()):
    """Only the existing primary seed model and fixed, declared holdout period.

    Optional prospective rows require explicit picks and both issued_at and
    published_at strictly before the archived event time. No such ledger is
    bundled. Duplicate event rows are conservatively excluded, never selected.
    """
    cutoff = datetime.combine(datetime.fromisoformat(as_of).date(), time.max, timezone.utc)
    first, last = evaluation['holdout']
    games = {g['id']: (g, season) for season in archive.values() for g in season['games']}
    def collect(source, prospective=False):
        duplicates = Counter(row.get('game_id') for row in source)
        rows, excluded = [], Counter()
        for prediction in source:
            year = prediction.get('season')
            if not prospective and (not isinstance(year, int) or not first <= year <= last):
                continue
            reason = None
            found = games.get(prediction.get('game_id'))
            if duplicates[prediction.get('game_id')] != 1:
                reason = 'duplicate_event'
            elif not found:
                reason = 'missing_game'
            else:
                game, season = found
                date = timestamp(game.get('date_utc'))
                p = prediction.get('p')
                if game['status'] != 'played' or game.get('winner') not in (game['a'], game['b']):
                    reason = 'unsettled_or_no_contest'
                elif not date or date > cutoff:
                    reason = 'unknown_or_future_event_time'
                elif year != game['season']:
                    reason = 'season_mismatch'
                elif not isinstance(p, (float, int)) or isinstance(p, bool) or not math.isfinite(p) or not 0 <= p <= 1:
                    reason = 'invalid_probability'
                elif prospective:
                    issued, published = timestamp(prediction.get('issued_at')), timestamp(prediction.get('published_at'))
                    if not issued or not published or not issued <= published < date:
                        reason = 'missing_or_late_publication'
                    elif prediction.get('pick') not in (game['a'], game['b']) or prediction.get('model') != 'seed':
                        reason = 'missing_declared_seed_pick'
                    elif prediction['pick'] != (game['a'] if p >= .5 else game['b']):
                        reason = 'inconsistent_declared_pick'
                    elif type(prediction.get('train_through')) is not int or prediction['train_through'] >= year:
                        reason = 'invalid_prior_training'
                    elif prediction.get('calibration_through') is not None and (type(prediction['calibration_through']) is not int or prediction['calibration_through'] >= year):
                        reason = 'invalid_prior_calibration'
                else:
                    model = historical.get(str(year), {}).get('seed', {})
                    train = prediction.get('train_through')
                    calibration = prediction.get('calibration_through')
                    if not isinstance(train, int) or train >= year or train != max(model.get('train_seasons', []), default=None):
                        reason = 'invalid_prior_training'
                    elif calibration != model.get('calibration_through') or (calibration is not None and calibration >= year):
                        reason = 'invalid_prior_calibration'
                    elif prediction.get('round') != game['round'] or prediction.get('y') != int(game['winner'] == game['a']):
                        reason = 'result_mismatch'
                if reason is None:
                    pick = prediction['pick'] if prospective else game['a'] if p >= .5 else game['b']
                    names = {team['id']: team['name'] for team in season['teams']}
                    rows.append(dict(game_id=game['id'], season=year, round=game['round'],
                                     round_name=game['round_name'], date_utc=date.isoformat().replace('+00:00', 'Z'),
                                     a=game['a'], b=game['b'], name_a=names[game['a']], name_b=names[game['b']],
                                     pick=pick, pick_name=names[pick], winner=game['winner'], winner_name=names[game['winner']],
                                     p_a=p, correct=int(pick == game['winner']),
                                     train_through=prediction.get('train_through'),
                                     calibration_through=prediction.get('calibration_through'),
                                     issued_at=prediction.get('issued_at') if prospective else None,
                                     published_at=prediction.get('published_at') if prospective else None,
                                     result_source=game.get('result_source')))
            if reason:
                excluded[reason] += 1
        rows.sort(key=lambda row: (timestamp(row['date_utc']), row['game_id']))
        return dict(totals=counts(rows), records=rows, points=calendar_points(rows), excluded=dict(excluded))

    historical_record = collect(predictions['seed'])
    prospective = collect(list(forecasts), True)
    holdout_games = [g for season in archive.values() for g in season['games'] if first <= g['season'] <= last]
    historical_record['coverage'] = dict(archived_games=len(holdout_games),
                                         no_contests=sum(g['status'] == 'no_contest' for g in holdout_games),
                                         eligible_games=historical_record['totals']['settled'])
    return dict(model='seed', as_of=as_of, holdout=[first, last], recent_games=RECENT_GAMES,
                rule='Higher saved matchup probability; exact 50–50 ties choose bracket-order side A.',
                order='UTC event time, then game ID for equal times. Weekly points include every eligible game in that week.',
                recent_rule='Last 20 eligible settled games through each point, reset each tournament; fewer games use their actual denominator.',
                historical=historical_record, prospective=prospective,
                legacy_half_credit_accuracy=evaluation.get('holdout_metrics', {}).get('seed', {}).get('accuracy'))


def track_summary(report):
    return {key: report[key] for key in ('model', 'as_of', 'holdout')} | {
        'historical': report['historical']['totals'], 'prospective': report['prospective']['totals']}
