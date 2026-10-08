"""Display-only scouting context from existing frozen form and prior seed snapshots.

No fitting, ranking of team ability, identity joins or new source collection.
"""
from datetime import datetime, timezone
from math import isfinite
from .model import predict


METRICS = ('elo', 'win_rate', 'margin')


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _frozen(feature, year):
    try:
        cutoff = datetime.fromisoformat(feature['cutoff_utc'])
        return cutoff == datetime(year, 3, 1, tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        return False


def field_form_context(season, features, team_id):
    """Midrank percentiles among covered archived entrants at the same cutoff."""
    year = season['season']
    team_feature = features.get(team_id, {})
    frozen = _frozen(team_feature, year)
    cohort = [features.get(team['id'], {}) for team in season['teams']]
    cohort = [feature for feature in cohort if _frozen(feature, year)]
    metrics = {}
    for name in METRICS:
        values = [f[name] for f in cohort if _number(f.get(name))]
        value = team_feature.get(name) if frozen else None
        if not _number(value):
            value = None
        percentile = None
        if value is not None and values:
            percentile = 100 * (sum(v < value for v in values) + .5 * sum(v == value for v in values)) / len(values)
        metrics[name] = dict(value=value, percentile=percentile, covered_teams=len(values))
    return dict(field_teams=len(season['teams']),
                cutoff_utc=team_feature['cutoff_utc'] if frozen else None,
                completed_games=team_feature.get('games') if frozen else None, metrics=metrics)


def add_scouting_context(state):
    """Enrich derived profiles only; paired probabilities use each game's prior model."""
    forecasts = {}
    for year, season in state['archive'].items():
        model = state['historical'].get(year, {}).get('seed')
        horizon = None
        if model:
            years = model.get('train_seasons', [])
            if not years or any(y >= int(year) for y in years):
                raise ValueError('Scouting seed snapshots must train strictly before their tournament.')
            horizon = max(years)
        for game in season['games']:
            probability = predict(model, game['seed_a'], game['seed_b']) if model and game['status'] == 'played' else None
            if probability is not None and (not isfinite(probability) or not 0 <= probability <= 1):
                raise ValueError('Invalid saved scouting probability.')
            forecasts[game['id']] = (game['a'], probability, horizon)
    for profile in state['team_profiles']['profiles'].values():
        for record in profile['appearances']:
            year = str(record['year'])
            record['form_context'] = field_form_context(state['archive'][year], state['features'].get(year, {}), record['archive_id'])
            scored = []
            for game in record['games']:
                first, probability, horizon = forecasts[game['id']]
                if probability is not None and record['archive_id'] != first:
                    probability = 1 - probability
                game['seed_probability'] = probability
                game['seed_trained_through'] = horizon if probability is not None else None
                if probability is not None:
                    scored.append(game)
            expected = sum(g['seed_probability'] for g in scored) if scored else None
            wins = sum(g['advanced'] for g in scored) if scored else None
            record['seed_expectation'] = dict(scored_games=len(scored), recorded_wins=wins,
                                            expected_wins=expected,
                                            difference=wins - expected if scored else None)
