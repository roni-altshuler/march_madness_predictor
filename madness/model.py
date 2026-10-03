"""Small symmetric ridge-logistic models; fixed domain scales, no outcome features."""
import math
import numpy as np

FEATURES = {
    "seed": ["seed difference / 15"],
    "seed_curve": ["seed difference / 15", "log seed ratio / log(16)"],
    "form": ["seed difference / 15", "pre-March Elo difference / 400", "win rate difference", "mean margin difference / 20"],
}


def sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -35, 35)))


def vector(a, b, kind="seed", fa=None, fb=None):
    if type(a) is not int or type(b) is not int or not 1 <= a <= 16 or not 1 <= b <= 16:
        raise ValueError("Seeds must be integers from 1 to 16")
    x = [(b-a)/15]
    if kind == "seed_curve":
        x.append(math.log(b/a)/math.log(16))
    elif kind == "form":
        if fa is None or fb is None:
            raise ValueError("Pre-tournament features missing; use seed model")
        x += [(fa['elo']-fb['elo'])/400, fa['win_rate']-fb['win_rate'], (fa['margin']-fb['margin'])/20]
    elif kind != "seed":
        raise ValueError("Unknown model")
    return x


def design(rows, kind, features):
    X, y, selected = [], [], []
    for g in rows:
        f = features.get(str(g['season']), {})
        fa, fb = f.get(g['a']), f.get(g['b'])
        if kind == 'form' and (fa is None or fb is None):
            continue
        X.append(vector(g['seed_a'], g['seed_b'], kind, fa, fb))
        y.append(float(g['winner'] == g['a']))
        selected.append(g)
    return np.asarray(X, dtype=float), np.asarray(y), selected


def fit(rows, kind, features):
    X, y, selected = design(rows, kind, features)
    if len(y) < 100:
        raise ValueError("At least 100 historical games required to fit")
    # No intercept: swapping opponents negates x and complements p exactly.
    coef = np.zeros(X.shape[1])
    ridge = 1.0
    for _ in range(80):
        p = sigmoid(X @ coef)
        grad = X.T @ (p-y) + ridge*coef
        hessian = (X.T * (p*(1-p))) @ X + ridge*np.eye(len(coef))
        step = np.linalg.solve(hessian, grad)
        coef -= step
        if np.max(np.abs(step)) < 1e-9:
            break
    return dict(kind=kind, features=FEATURES[kind], coef=coef.tolist(), temperature=1.0,
                n_train=len(y), train_seasons=sorted({g['season'] for g in selected}), ridge=ridge)


def predict(model, a, b, fa=None, fb=None):
    return float(sigmoid(np.dot(vector(a, b, model['kind'], fa, fb), model['coef']) / model.get('temperature', 1)))


def calibrate(model, prior_predictions):
    """Temperature selected only from strictly earlier rolling predictions."""
    if len(prior_predictions) < 189:
        return dict(model, temperature=1.0, calibration_n=0)
    p = np.clip([r['p'] for r in prior_predictions], 1e-6, 1-1e-6)
    y = np.asarray([r['y'] for r in prior_predictions])
    logits = np.log(p/(1-p))
    grid = np.linspace(0.75, 1.5, 61)
    losses = [np.mean(np.logaddexp(0, logits/t) - y*logits/t) for t in grid]
    return dict(model, temperature=float(grid[int(np.argmin(losses))]), calibration_n=len(y),
                calibration_through=max(r['season'] for r in prior_predictions))


def metrics(rows):
    if not rows:
        return None
    p = np.clip([r['p'] for r in rows], 1e-8, 1-1e-8)
    y = np.asarray([r['y'] for r in rows])
    # Mirror orientation for a symmetric reliability curve; effective n stays unmirrored.
    cp, cy = np.r_[p, 1-p], np.r_[y, 1-y]
    bins = []
    for lo in np.arange(0, 1, 0.1):
        mask = (cp >= lo) & (cp < lo+0.1 if lo < .9 else cp <= 1)
        bins.append(dict(lower=round(float(lo), 1), count=int(mask.sum()),
                         predicted=float(cp[mask].mean()) if mask.any() else None,
                         observed=float(cy[mask].mean()) if mask.any() else None))
    ece = sum(b['count']*abs(b['predicted']-b['observed']) for b in bins if b['count'])/len(cp)
    return dict(n=len(y), brier=float(np.mean((p-y)**2)),
                log_loss=float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p))),
                accuracy=float(np.mean(np.where(p==.5, .5, (p>.5)==y))), ece=ece, calibration=bins)
