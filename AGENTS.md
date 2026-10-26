# AGENTS.md

Guidance for AI coding agents working in this repo. This file covers **how to work here**; for
*what the project is* (Monitor My Watershed, the ODM2 Data Sharing Portal) see
[README.md](README.md) and the [deployment guide](doc/deployment_guide.md). How a multi-step round
runs is in the
[shared workflow guide](https://github.com/LimnoTech/limno-agent-skills/blob/main/agent-workflow.md);
where it and this file disagree, this file wins on anything local to this repo and the guide wins
on process. **That guide and the other `LimnoTech/limno-agent-skills` links below are in a private
LimnoTech repository**; contributors outside LimnoTech can't open them, so the guardrails,
branching, ledger and verification rules for this repo are stated in this file.

## What kind of repo this is

A **public, open-source Django web application** in the `WikiWatershed` GitHub organization, run
in production at <https://monitormywatershed.org>. It is not one of LimnoTech's pixi-based
analysis repos: there is no pixi, no notebooks and no package to install. Its users are the
EnviroDIY and Leaf Pack communities, whose dataloggers post data to it around the clock, so a
change that reaches `main` reaches a live service.

## ⚠️ Critical guardrails — read before any work

- **Agents commit on a branch. Agents never push, never merge, and never work on `main`.**
  Commit messages carry **no AI co-author trailer**. The reasons are in the
  [shared workflow guide](https://github.com/LimnoTech/limno-agent-skills/blob/main/agent-workflow.md#the-task-group-gate).
  *These written rules are the only enforcement: there is no hook stopping you.*
- **Never connect to the production or staging servers or databases.** The production database
  holds over a billion time-series values ([#740](https://github.com/WikiWatershed/monitor-my-watershed/issues/740));
  an exploratory query or an `UPDATE` against it can take the site down. Anything that must run
  there is written up for a person to run.
- **This repo is public; credentials live elsewhere.** Real settings are in a git-ignored
  `src/WebSDL/settings/settings.json`, symlinked from a separate private config repo (see the
  [deployment guide](doc/deployment_guide.md)). Never commit a settings file, a hostname, an
  instance ID, a key or a password, and never quote the private config repo into this one, an
  issue or a PR.
- **Issues and PR descriptions are public too.** Draft them for a person to post.

## Environment

- **conda, from [environment.yml](environment.yml).** It pins `pandas < 2.0`,
  `sqlalchemy >=1.4.0,<2.0` and `django<4.0` (via pip). Treat those pins as load-bearing: the
  code uses SQLAlchemy 1.x calling conventions (e.g. `connection.execute(query, **kwargs)`).
- **Settings:** `manage.py` and `wsgi.py` default to `WebSDL.settings.linux_server`; every
  settings module reads `settings.json` (template:
  [settings_template.json](src/WebSDL/settings/settings_template.json)). Nothing imports without
  one.

## Code map

| Path | What it holds |
| --- | --- |
| [src/dataloaderservices/](src/dataloaderservices/) | REST endpoints: streaming POSTs (`TimeSeriesValuesApi`, `/api/data-stream/`), CSV upload (`SensorDataUploadView`, `/api/data-file-upload/<id>`), CSV download (`CSVDataApi`), and the raw-SQL bulk insert `insert_timeseries_result_values_bulk` |
| [src/dataloaderinterface/](src/dataloaderinterface/) | Site, sensor and registration pages (Django ORM models) |
| [src/dataloader/](src/dataloader/) | Django models of the ODM2 schema, and the custom test runner |
| [src/odm2/](src/odm2/) | SQLAlchemy models and CRUD for the ODM2 schema |
| [src/timeseries_visualization/](src/timeseries_visualization/) | The TSV plotting page (`/tsv/`) |
| `src/leafpack/`, `src/streamwatch/` | Leaf Pack and StreamWatch macroinvertebrate surveys |
| `src/accounts/` | AWS Cognito sign-in |
| `src/hydroshare/`, `src/hydroshare_util/` | HydroShare export |

**Two database layers.** Django's ORM serves the pages; the time-series path uses a module-level
SQLAlchemy engine (`_db_engine` in [dataloaderservices/views.py](src/dataloaderservices/views.py))
and raw SQL into `odm2.timeseriesresultvalues`, a TimescaleDB hypertable with compressed
(columnstore) chunks. The database runs on its own server, separate from the web app
([deployment guide](doc/deployment_guide.md)). TimescaleDB upgrade and configuration history:
[#740](https://github.com/WikiWatershed/monitor-my-watershed/issues/740),
[#744](https://github.com/WikiWatershed/monitor-my-watershed/issues/744),
[#769](https://github.com/WikiWatershed/monitor-my-watershed/issues/769).

## Workflow

- **The round structure lives in
  [`agent-workflow.md`](https://github.com/LimnoTech/limno-agent-skills/blob/main/agent-workflow.md)**
  — task-groups, gates, worktrees, review, the ledger. Read it before a multi-step plan.
- **Branches:** feature and fix branches merge into `develop`, which merges into `main` for
  release; hotfixes branch off `main`. A round's branch starts from `main` unless `develop` has
  diverged from it, in which case start from `develop` and say so. A person merges it, by PR,
  into `develop`, not `main`; this overrides the shared guide's "the integration branch merges
  to `main`".
- **The ledger** goes in `.superpowers/sdd/progress.md` (git-ignored).
- **Specs and plans** from the superpowers cycle go in `doc/superpowers/specs/` and
  `doc/superpowers/plans/`. This repo uses `doc/`, not `docs/`.
- **Research** (technology assessments, upgrade studies) follows the
  [research skill](https://github.com/LimnoTech/limno-agent-skills/blob/main/skills/research/SKILL.md).
  The document goes in `doc/research/<topic>.md`; its log and any scripts go beside it in
  `doc/research/<topic_with_underscores>/`, since this repo has no sandbox folder.

## Verification

There is **no CI and no runnable local test suite out of the box**: the tests
(`src/*/tests/`, `src/*/tests.py`) need a `settings.json` and a PostgreSQL server, and
`TEST_RUNNER` is set only in `WebSDL.settings.development`. So:

- **Always:** `python -m compileall -q src/<app>` on every app you touched, in the conda
  environment.
- **When a `settings.json` and a local database exist:**
  `cd src && python manage.py check --settings=WebSDL.settings.development`, then
  `python manage.py test <app> --settings=WebSDL.settings.development`.
- **Say in every hand-back which of these ran.** "Compiles" is not "tested"; never let a summary
  imply a test run that did not happen.

## Gotchas

Tool gotchas shared across LimnoTech repos (pandas, pyarrow, …) live in the
[shared python-stack-gotchas guide](https://github.com/LimnoTech/limno-agent-skills/blob/main/python-stack-gotchas.md).
This section lists only what is specific to this repo.

### Learned in this repo

- **The `.gitignore` pattern `settings.json` also ignores `.claude/settings.json`.** It is there
  for the Django secrets file; `!.claude/settings.json` re-includes the Claude Code setting.
- **`migrations/` is git-ignored** repo-wide: no Django migration is tracked here, so a model
  change ships with no migration file for reviewers to read. Say how the schema change reaches
  the database in the PR.
- **CSV uploads are parsed row by row with `csv.reader`, not pandas,** and flushed to the
  database every 100,000 values through a temporary table and `INSERT … SELECT … ON CONFLICT DO
  NOTHING`. Memory behaviour of that path is the subject of
  [#769](https://github.com/WikiWatershed/monitor-my-watershed/issues/769) and the research in
  `doc/research/`.
