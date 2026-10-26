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

## 2026-10-25 (after hand-back of Revision 1)

- Anthony Aufdenkampe, reviewing Revision 1, asked whether #8074 and #10632 are relevant memory
  improvements after 2.19. Controller checked:
  - PR #8074 "Use correct memory context during flush", merged 2025-05-08 (`gh api
    repos/timescale/timescaledb/pulls/8074`): "row_compressor_flush was called without switching
    to per-row memory context causing memory leaks in the ExprContext memory context. This in
    turn would cause problems with recompression when there were a lot of small batches."
  - 2.19.3 source tarball: `row_compressor_flush` is called from `compression.c` lines 485, 875,
    902; reached via `row_compressor_append_sorted_rows` from `recompress.c` line 694 and
    `hypercore/hypercore_handler.c` lines 2202 and 3797. Recompression of a Hypercore chunk goes
    through `compression/api.c` `compress_hypercore` → `tsl_compress_chunk_wrapper` (lines
    861–873). So the #8074 leak is on production's post-upload recompression path [V code; I for
    relevance]. Leak size per flush not found.
  - PR #10632 "Move chunk rows to columnstore as DML", merged 2026-09-25: an incremental,
    interruptible alternative to `compress_chunk` holding ShareUpdateExclusiveLock (does not block
    INSERT/UPDATE/DELETE); resumes from partial state. Lives in `_timescaledb_functions`
    (internal); the 2.31.0 policy still calls `compress_chunk`.
- Pending for Revision 2 (agreed with Anthony Aufdenkampe; held until all his feedback is in):
  1. Summary bullet 1: keep "no release note claims lower memory for the insert itself"; add that
     2.20.0 fixes a memory leak in the code that recompresses chunks after an upload, a plausible
     cause if crashes come during the compression job.
  2. Q1 table #8074 row: in 2.19.3 the leaking code also recompresses Hypercore chunks; cite the
     call path above.
  3. Q1 table #10632 row and Recommendation 6: `move_to_columnstore()` as a non-blocking,
     memory-capped alternative to `compress_chunk` for operator-run backfills; internal-API
     caveat.
  4. Q1 Answer: one sentence that the upgrade does address a known memory leak, in the
     compression step rather than the insert.
  5. Open questions: the #8074 leak's memory cost per batch (staging measurement or crash logs).
- Instruction for Revision 2 (Anthony Aufdenkampe): the body states only current understanding;
  earlier states appear only in the revision history.
- Anthony Aufdenkampe asked for more on using pyarrow to "sort, group and de-duplicate before
  sending". Controller checked (apache-arrow-26.0.0 raw sources): `table.pxi` has
  `Table.sort_by` (line 2112), `filter`, `take`, `drop_null`, `group_by` (line 5636; "When set
  to True (the default), no stable ordering of the output is guaranteed"), `aggregate`; no
  `drop_duplicates` (grep "duplicate" finds only to_pydict notes). `docs/source/cpp/compute.rst`:
  `is_in`, `index_in`, `unique`, `drop_null`, `sort_indices`, `hash_first`/`hash_last`
  ("(11) Result is based on ordering of the input data."). `_csv.pyx`: `WriteOptions
  include_header` (default True). PyPI JSON: pyarrow 25.0.1 (2026-08-10) is the last release
  with cp310 wheels; 26.0.0 (2026-10-09) has none.
- Pending for Revision 2:
  6. Question 2: add a short section on the workflow — wide CSV means grouping by sensor is
     per column; sort via `sort_indices`/`take`; de-duplicate within file on sorted timestamps
     (keep first, matching DO NOTHING); split by real chunk ranges
     (`timescaledb_information.chunks`); de-duplicate against the database per (resultid, chunk)
     with a read query and `pc.is_in`, skipping windows already stored; COPY only new rows
     (`write_csv` include_header=False → `copy_expert` FORMAT csv) and keep ON CONFLICT DO
     NOTHING as a safety net; streaming by chunk boundary when the file is time-ordered.
     Caveats: pandas 1.x can do the same logic; Python 3.10 caps pyarrow at 25.0.1; mixed date
     formats; the read-vs-conflict-check cost is unmeasured (add to the staging test and Open
     questions).
- Anthony Aufdenkampe asked for steps in order of return on effort (limited funds), and the value
  of stopping at TimescaleDB 2.21. Controller checked:
  - PostgreSQL 17 `doc/src/sgml/runtime.sgml` (REL_17_STABLE, "Linux Memory Overcommit"): "If a
    child process is terminated, PostgreSQL will typically terminate all remaining connections
    and either recover automatically, if restart_after_crash is enabled, or shut down";
    `sysctl -w vm.overcommit_memory=2` "will lower the chances significantly"; postmaster
    `oom_score_adj` -1000 with `PG_OOM_ADJUST_FILE`/`PG_OOM_ADJUST_VALUE`; more swap helps; too
    many connections can be the cause.
  - TimescaleDB 2.21.4 `chunk_dispatch.c` line 393 still has `if (!cis->use_tam)`, so #7972 and
    #8182 (conflict-check path) do not apply to Hypercore tables on 2.21.4 [V code; I effect].
  - CHANGELOG: 2.21.4 (2025-09-25) is the last 2.21.x; #8196 (2.21.0) deprecation warning for
    TAM; #9455 ColumnarScan leak fix in 2.26.1. #10580 (2.30.1) concerns bloom indexes only
    (PR body) — not relevant here.
  - `views.py` line 54: `create_engine(..., pool_size=10, ...)`.
  - #744 SQL: PRIMARY KEY (resultid, valuedatetime) plus a separate UNIQUE INDEX on the same
    columns — redundant [V]; double conflict checks under untargeted ON CONFLICT [I].
- Pending for Revision 2:
  7. Restructure Recommendations in order of return on effort, with rough effort [I]:
     (1) read crash evidence; (2) OOM-killer hardening per PG docs (overcommit=2, postmaster
     oom_score_adj, swap; check max_connections × work_mem vs RAM); (3) drop the redundant unique
     index; (4) advisory-lock one upload at a time, smaller ordered INSERT…SELECT, optional size
     cap; (5) 2.21.4 + SET ACCESS METHOD heap, with a table contrasting "2.21 on Hypercore" vs
     "2.21 + heap" and what stopping at 2.21 misses; (6) de-duplicate against the database
     (pending item 6); (7) later: 2.31, a job queue, pandas/SQLAlchemy/Django.
- Anthony Aufdenkampe: ptomasula has the crash logs and has started on them; a checklist of what
  to look for is useful. Controller checked strings: PostgreSQL REL_17_STABLE `postmaster.c`
  "%s (PID %d) was terminated by signal %d: %s" (procname e.g. "server process"), errdetail
  "Failed process was running: %s", "terminating any other active server processes" (line
  2879), "all server processes terminated; reinitializing" (line 3360); `mcxt.c` errmsg "out of
  memory", errdetail "Failed on request of size %zu in memory context \"%s\"", "TopMemoryContext".
  TimescaleDB 2.19.3: views `timescaledb_information.job_stats`, `job_errors` ("job crash
  detected, see server logs"), `jobs`, `chunks`; compression job application_name "Compression
  Policy" (`tsl/src/bgw_policy/compression_api.c` line 289). Log file locations [U] (data
  directory is non-default per the private config wiki).
- Pending for Revision 2:
  8. Recommendation 1: add the log checklist (which process was killed and its SQL; OOM errors
     with memory-context dump; job_errors/job_stats; correlate with upload POSTs; baseline
     settings, PG minor, swap, overcommit).
- Anthony Aufdenkampe liked the detailed steps for de-duplicating against the database before
  inserting. Pending item 6 amended: give the steps in detail, each with its pyarrow and its
  pandas 1.x form (pandas API names to be checked against pandas 1.5.3 docs when written).
- Revision 2 written (pending items 1–8). Controller checks for new claims: pandas 1.5.3 is the
  last 1.x (PyPI, 2023-01-19, requires_python >=3.8); v1.5.3 `read_csv` has `skiprows`,
  `chunksize`; `DataFrame.drop_duplicates(subset, keep="first")`, `sort_values`, `dropna`,
  `Series.isin`, `NDFrame.to_csv` exist. TimescaleDB 2.19.3 `sql/views.sql`
  `timescaledb_information.chunks` has `hypertable_name`, `chunk_name`, `range_start`,
  `range_end`, `is_compressed`.
- Anthony Aufdenkampe asked about the Hypercore "experiment failing", given the effort in #744.
  Controller checked CHANGELOG: 2.27.0 "The Hypercore engine now supports a vectorized
  implementation of filters…" (engine name continues); 2.22.0 "we learned that btrees were not
  the right architecture … close to or on par with TAM without needing to store an additional
  index". Added a section "What the conversion changes, and what it keeps" to Revision 2: the
  #744 columnstore settings (chunks, segmentby, orderby, policy, PK, de-duplicated data) are
  kept [I; PR #8341 says data stays in the columnstore], only the TAM's B-tree coverage of
  compressed rows goes; #744's reported gains followed the whole 2.7→2.19 + PG17 +
  reconfiguration, with no measurement of the TAM's share.
- Anthony Aufdenkampe asked for more on the Hypercore reversion in this revision. Controller
  checked: CHANGELOG `## 2.18.0 (2025-01-23)` (TAM introduced, per the 2.21.0 note), `## 2.21.0
  (2025-07-08)` "Sunsetting of the hypercore access method … will be sunsetted in TimescaleDB
  2.22.0, scheduled for September 2025" with the migration DO block; `## 2.22.0 (2025-09-02)`
  #8364 "Remove hypercore table access method". TimescaleDB 2.21.4 `sql/views.sql` line 369
  `timescaledb_information.hypertable_compression_settings` (columns hypertable, segmentby,
  orderby, compress_interval_length); line 418 `hypertable_columnstore_settings`. Pending for
  the review-fix wave: expand the reversion section (timeline, procedure on staging, checks
  afterwards).
- Anthony Aufdenkampe: the columnstore-engine vs TAM distinction belongs in the Summary;
  "Production uses the Hypercore storage method" is not correct as written. Asked for a full
  pass clarifying such statements. Pending for the review-fix wave: define "columnstore
  (Hypercore engine)" and "Hypercore table access method (TAM)" once near the top; rewrite the
  Summary with them; replace "Hypercore storage", "standard storage", "convert to standard
  storage", "Hypercore tables/chunks" throughout with precise terms (switching the access
  method to heap keeps data compressed in the columnstore). Then a fresh full-document review.
  Still Revision 2 (not yet handed back).
- Review of Revision 2 draft (fresh Opus): 0C/7I/22M; all applied in a full rewrite with the
  terminology pass and the expanded TAM reversion section. Controller re-checked: 2.31.0
  `src/guc.c` line 1202 `enable_in_memory_recompression` boot `true`; 2.19.3 `src/bgw/job.c`
  line 1470 `"%s [%d]"`; 2.31.0 `src/nodes/modify_hypertable.c` line 60 unique-index check;
  pyarrow apache-arrow-25.0.1 `table.pxi`, `compute.rst`, `_csv.pyx`, `options.h` line 153
  have the same APIs; 2.21.4 `views.sql` `chunks` has `hypertable_schema`, `jobs` has
  `application_name`, `hypertable_name`; `views.py` lines 353–357, 432–434 (UTC shift),
  312–314 (header rows skipped anywhere). Ruling on M22: the config repo's name is already
  public in `doc/deployment_guide.md` line 14, and a 2018 server size is not sensitive; kept,
  flagged to the requester.
- Anthony Aufdenkampe: what about 2.21.4 keeping the TAM; budget 8–16 hours. Added "With only
  8–16 hours" under Recommendations.
