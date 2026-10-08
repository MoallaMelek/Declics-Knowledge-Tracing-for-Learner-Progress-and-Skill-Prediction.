# Working together on DÉCLIC Axis 7

This repository contains the learner progress and skill prediction axis. Other axes remain independent until their observation interfaces are ready for integration.

## Semester workflow

- Keep `main` runnable. Work on a short-lived branch for each change and open a pull request describing the problem, change, and validation.
- Review changes to the observation contract together. The canonical boundary is `axis7/schema.py`; regenerate its JSON Schema with `python -m axis7.schema` and update the example and integration guide when it changes.
- Preserve separation between the public software-engineering benchmark, synthetic musical demonstration, and any future consented project observations.
- Never commit runtime learner events, credentials, raw partner recordings, or identifiable learner data.
- Record actual results and limitations. Changes to model architecture or vocabulary require compatible checkpoints and evaluation.

## Verification

Install the dependencies as described in README.md, then run `python -m pytest`. Node.js enables the frontend state regression test. Test temporary directories must be writable.

## Integration with the other axes

Start with `docs/INTEGRATION.md`, `schemas/attempt-v1.schema.json`, and `examples/project-attempt.json`. Upstream axes own perception, confidence and rubric definitions; Axis 7 consumes structured observations. Agree on exercise identifiers, skill mappings, timestamps and provenance before combining modules.

## Reuse

The included FORGET-SE data has its own CC BY 4.0 attribution in `data/DATA_LICENSE.md`. No software license has been selected for the project's original code yet; public visibility alone does not grant a reuse license.
