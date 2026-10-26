# Research log: TimescaleDB upgrade and CSV-upload memory

**Question:** Would upgrading TimescaleDB from 2.19 to the latest release stop large CSV uploads
from exhausting memory on the database server, and how could pandas 2/3 with pyarrow complement
that? **For:** Monitor My Watershed developers (Anthony Aufdenkampe, Paul Tomasula).
**Decision it informs:** whether and how to do issue #769, and what else to change alongside it.
**Out of scope:** benchmarks; changes to the production server; a full design of the new upload
path (a later spec).
**Depth:** desk, as stated in the request by Anthony Aufdenkampe on 2026-10-25 (the request asked
for independent work, so the scope Q&A was replaced by the request itself; ledger ruling 1).
**Plan:** three parallel Sonnet research subagents (TimescaleDB releases; backfill memory
mechanism; pandas/pyarrow), roughly an hour; controller checks quotes, writes the document; one
fresh review subagent. **Document:**
[`timescaledb-upgrade-csv-upload-memory.md`](../timescaledb-upgrade-csv-upload-memory.md)

## 2026-10-25

- Seed: issue #769 (`gh issue view 769`): asks for 2.19 → >=2.26; cites the 2.20 and 2.21 blog
  posts; no comments; no description of the crash itself.
- Seed: issue #744 comments (`gh issue view 744 --json comments`): ptomasula's 2025-05-01
  configuration — 30-day chunks; `SET ACCESS METHOD hypercore`; segmentby `resultid`, orderby
  `valuedatetime`; columnstore policy after 7 days; PK and a unique btree index on
  (resultid, valuedatetime). Used for the table definition. aufdenkampe's 2025-09-24 comment:
  ~50% CPU drop after the upgrade.
- Seed: issue #740: upgrade path 2.7 → 2.15.3 → PG16 → 2.19 → PG17; released 2025-05-01.
- Code read: `src/dataloaderservices/views.py` at `82baf4d` — `SensorDataUploadView.post`
  (lines 364–503) and `insert_timeseries_result_values_bulk` (lines 1116–1153). Row-by-row
  `csv.reader`; flush when the list exceeds 100,000 values; temp table + `copy_from` +
  `INSERT … SELECT … ON CONFLICT DO NOTHING`, one transaction per flush.
- Code read: `environment.yml` — `pandas < 2.0`, `sqlalchemy >=1.4.0,<2.0`, `django<4.0`,
  `python >=3.10.4`.
- Code read: `doc/deployment_guide.md` — web app and database on separate servers.
- Decision: research briefs in the ledger workspace (`.superpowers/sdd/briefs/`), returns in
  `.superpowers/sdd/returns/` (git-ignored working files; the claims used are re-checked here).
- Script: `batch_memory.py` (Python 3.13.15, stdlib only; `python -I …`). One flush batch of
  100,008 values (8 sensors per row): list of objects 22.6 MiB (237 B/value); list + StringIO
  29.3 MiB peak; COPY text 5.5 MiB (58 B/value); typed columns would be 2.7 MiB (28 B/value,
  calculated). Conclusion [I]: the web app holds ~30 MiB per flush, so the web-side Python is not
  where gigabytes go; a pandas/pyarrow parser saves tens of MiB on the web server, not on the
  database server.
- Dispatched briefs A, B, C (Sonnet, background).
- Seed (private): the LimnoTech `ODM2DataSharingPortalConfig` repo and its wiki, pointed to by
  Anthony Aufdenkampe on 2026-10-25 as possibly out of date. Last commits 2022-10-11 (repo) and
  2022-05-27 (wiki), both before the 2025 rebuild. Wiki "Server-Architecture" (2018 notes):
  database server "6 CPU, 16 GB RAM, 100 GB Hard Disk" — [U] for today's server. Wiki
  "Upgrade PostgreSQL 12 to 13 (with TimescaleDB 2.6)": memory settings were set with
  `timescaledb-tune`. No postgresql.conf, instance type or 2025 configuration in either.
  Only non-secret facts used; credential files not opened.
- Return C (pandas/pyarrow) received. Controller re-checked from raw sources:
  v2.2.0.rst line 486 `| sqlalchemy | 2.0.0 |`; v2.1.4 `_optional.py` `"sqlalchemy": "1.4.36"`
  (return C quoted 2.0.3's 1.4.16; 2.1.x needs 1.4.36); v3.1.0 `pyproject.toml`
  `requires-python = '>=3.11'`; v3.1.0 `readers.py` lines 377/382 reject `iterator`/`chunksize`
  with the pyarrow engine; PyPI latest pandas 3.1.0 uploaded 2026-10-22. All confirmed.
  Return C's own 192 B/value probe differs from `batch_memory.py`'s 237 B/value (its datetimes
  and strings differ); the document uses `batch_memory.py`.
- Return B (memory mechanism) received. Controller re-checked from raw sources:
  `main` CHANGELOG.md — latest `## 2.31.0 (2026-10-20)`; line 913 (2.22.0): "Hypercore TAM was an
  experiment and it did not show the performance improvements we hoped for. It is removed with
  this release. Upgrades to 2.22.0 and higher are blocked if TAM is still in use."; line 928
  migration `alter table %s set access method heap`. `src/guc.c` at 2.19.3:
  `max_tuples_decompressed_per_dml_transaction` boot 100000, "0 sets this value to unlimited";
  `hypercore_arrow_cache_max_entries` boot 25000. `chunk_dispatch.c` at 2.19.3 line 442:
  `if (!cis->use_tam) ts_chunk_dispatch_decompress_batches_for_insert(...)`. All confirmed.
  Not re-checked by controller (taken as return B's [V] quotes, re-checkable from its locators):
  issue #4903/PR #4931 containment, #7270, #8074, #8182, #9455, #8400 timings, docs backfill
  procedure, PG17 config.sgml quotes, timescaledb-tune formulas.
- Key consequence [I]: the root cause of the 2.19 crash is not established by any upstream
  issue; the production TAM path is unusual (removed upstream), so the most defensible fix is to
  leave TAM (required anyway to upgrade) and change the backfill procedure.
- Return A (releases) received. Controller re-checked from raw sources: PR #8341 (`gh api
  repos/timescale/timescaledb/pulls/8341`) merged 2025-07-07, body "data will now remain in the
  columnstore if using `ALTER TABLE ... SET ACCESS METHOD heap` … no data is rewritten. Only
  indexes need to be rebuilt"; review comment quoting the old code comment "(currently) delete
  the compressed chunk when changing the table access method"; `src/compat/compat.h` at 2.31.0
  `is_supported_pg_version_17(version) ((version >= 170003) && …)`; `src/copy.c` at 2.31.0
  lines 843–846 "disabling direct compress because the destination table has unique";
  `sql/updates/2.21.3--2.22.0.sql` at 2.22.0 lines 2–9 RAISE EXCEPTION "TimescaleDB does no
  longer support the hypercore table access method. Convert all tables to heap access method
  before upgrading." All confirmed. Return A's blog quotes (3,000-row benchmark) and its
  changelog entries (#7972, #8182, #8074, #8569, 2.24.0 bloom note, #10666) taken from its
  quotes with locators; not re-fetched.
- Rejected: return A's aside that "the dominant memory consumer is likely the web-app process"
  — contradicted by `batch_memory.py` (~30 MiB per flush).
- Probe (controller, desk): read `tsl/src/hypercore/arrow_cache.c` and `arrow_tts.c` at 2.19.3.
  The Arrow cache is created per Arrow slot (`arrow_tts.c` line 120,
  `arrow_column_cache_init(&aslot->arrow_cache, slot->tts_mcxt)`) and deleted when the slot is
  released (line 144). PostgreSQL's unique check makes and drops its own slot per call, so the
  25,000-entry cache is not, on this reading, an accumulator across rows. [I] Not traced
  further: where decompression memory for a conflicting TAM row is allocated. Conclusion: the
  root cause cannot be settled at desk depth; recommend a measurement (memory-context dump) on
  a staging copy. Hypothesis "Arrow cache fills" dropped from the document.
- Decision: marker density = reference (this is an assessment), facts in tables.
- Review 1 (fresh Opus subagent): 1 Critical, 5 Important, 11 Minor; all accepted and fixed in
  Revision 1 before hand-back. C1 re-checked by the controller: `compression_dml.c` at 2.19.3
  increments `stats.tuples_decompressed` only at line 548 (rows moved into the rowstore);
  `batch_matches` (line 504) resets non-matching batches and returns early on DO NOTHING
  (lines 515–520). So the 100,000 cap does not bound this insert; the "memory guard" claim was
  removed. I1 "Old API" tag re-checked: `modify-data-in-hypercore.md` at `a28536b` imports
  `Deprecated2200` ("Old API since TimescaleDB v2.20.0"); `gh api repos/timescale/docs` →
  `archived: true`. M6 re-checked: `grep -rn read_sql src` → 4 call sites in 3 files.
  I5: `gh repo view LimnoTech/limno-agent-skills` → PRIVATE (AGENTS.md now says so).
- Review 2 (fresh Opus, scoped to the fix diff): 0 Critical, 1 Important, 5 Minor; all fixed.
  Important re-checked by controller: at 2.31.0 the policy job calls `compress_chunk`
  (`sql/policy_internal.sql` line 211); `move_to_columnstore` is the internal
  `_timescaledb_functions.move_to_columnstore()` (`sql/maintenance_utils.sql` line 67). So the
  new sort limit does not bound the policy job; claim withdrawn from Summary and Answer.
  #740 opened 2025-03-18, #744 2025-03-25 (`gh issue view --json createdAt`). Issue #8775 body
  (a user, not a maintainer) says converting to rowstore "could bloat the disk size and memory".
- Review 3 (fresh Opus, scoped): 0C/0I/2M; both are citation fixes, reviewed by controller (compression.c 2.31.0 line 3781 reads move_to_columnstore_tuple_sort_limit; guc.c 2.19.3 lines 591-596 define enable_dml_decompression_tuple_filtering, default true); footnote set check and batch_memory.py rerun pass.
