# Research

Standalone analysis that the dashboard's models are based on. These scripts run
independently of the app — they were used to build and validate the logic that
later shipped in `backend/services/`.

## `inventory-impact/`

Event studies on how crude prices react to the weekly EIA inventory release:
measuring abnormal returns around the print, separating the macro component,
checking whether the reaction depends on the prevailing regime, and validating
the result out of sample. This is what backs the `/api/release-impact` endpoint.

Start with [`00_HANDOFF.md`](inventory-impact/00_HANDOFF.md) for the writeup and
[`09_SCORING_REPORT.md`](inventory-impact/09_SCORING_REPORT.md) for results.

## `spread-models/`

Fair-value modelling for calendar spreads and butterflies — a structural model
of the curve plus a mixture model for regime behaviour, with scoring and figure
generation. This is what backs the paper-trading engine in `backend/strategy/`.

See [`spread-models/README.md`](spread-models/README.md) and the generated
[`output/report.md`](spread-models/output/report.md).

## Running

These are exploratory scripts, not a package. They need the extra dependencies
in `inventory-impact/requirements-research.txt` on top of the backend's.
