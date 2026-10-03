# Working in March Lab

- Men's NCAA Division I only. Never invent fixtures, teams, results, statistics or metrics.
- Archive coverage and feature coverage are separate. Missing years/fields remain explicit.
- Training, transforms, calibration and model selection must use strictly earlier information.
- Preserve baselines and compare challengers on identical game IDs.
- Preserve the unknown 2027 field until its real bracket is imported. The announced format is 76 teams with 12 Opening Round games.
- Historical 64-team simulations are conditional on preliminary-round survivors.
- Source changes require provenance, attribution, SHA-256 hashes and a fresh evaluation.
- Keep raw schedules and user imports ignored. Never commit credentials or Kaggle data.
- UI probabilities must appear as numbers; missing values render as a dash.
- Run `python -m pytest -q`, `node --check web/app.js` and `python tests/browser_check.py` for affected changes.
- Public repository and free GitHub Pages publication are user-authorized for this project. Keep source/data attribution and audit files/history before publication. No paid plans or changes to unrelated repositories. Follow-on work uses branches and draft PRs.
