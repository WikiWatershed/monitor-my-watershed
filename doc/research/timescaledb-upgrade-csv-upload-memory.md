# TimescaleDB upgrade and memory exhaustion during large CSV uploads

**Revision 2, 2026-10-25.** Anthony Aufdenkampe, LimnoTech (requested the work); drafted with
Claude (Claude Code). Revision 1 was reviewed by Anthony Aufdenkampe; Revision 2 is not yet
reviewed by a person. Markers: [V] checked against a cited source opened for this work or a
probe run for it; [I] derived or inferred, including results of the scripts in the working
record; [U] not checked. Sources accessed 2026-10-25. Marker density: reference.
Working record: [log, scripts](timescaledb_upgrade_csv_upload_memory/).
History: [Appendix](#appendix-revision-history).

## Summary

Large CSV uploads of historical logger data have been crashing the Monitor My Watershed
database server by exhausting its memory. Issue #769 proposes upgrading TimescaleDB from 2.19
to 2.26 or later. This document asks whether that upgrade would stop the crashes, what it would
take, how moving the web app to pandas 2 or 3 with pyarrow could help, and, since funds are
limited, which steps give the most return for the effort. It is desk research: documentation,
release notes, issue trackers and source code were read, and nothing was run against a
database. The terms used are defined [below](#terms).

- **Upgrading alone is not shown to stop the crashes** [I]. It fixes a known memory leak in the
  code that recompresses chunks after an upload (#8074, in 2.20.0) [V], but no release note
  claims lower memory for the upload's insert itself [V]. Whether that leak is the cause
  depends on which process the crash logs show dying ([step 1](#1-read-the-crash-evidence)) [I].
- **What the upgrade involves.** Production stores its data with TimescaleDB's Hypercore
  engine, which keeps recent data in row form and compresses older chunks into a columnstore;
  since #744 it has also used the experimental Hypercore *table access method* (TAM) [V].
  TimescaleDB removed only the TAM, in 2.22.0, and refuses upgrades past 2.21 while any table
  uses it [V]. On 2.21 the access method can be switched back to PostgreSQL's standard heap
  without rewriting the data, which stays compressed in the columnstore [V], so the #744
  columnstore settings stay too [I]. The in-place upgrade to 2.21.4 is cheap; the switch should
  be too, but locks the table while it runs and is untimed [I]. The faster conflict checks of
  2.20–2.21 only apply after the switch [V for the code; I for the effect].
- **With 8–16 hours** ([plan](#with-only-816-hours)) [I]: read the crash evidence; set Linux's
  strict memory overcommit, which PostgreSQL's documentation recommends and which turns most
  memory kills, each of which restarts the whole database server, into one failed statement
  [V for the documentation; I for the effect]; drop a duplicate unique index; upgrade to 2.21.4
  keeping the TAM, which brings the #8074 fix; and time the switch on staging, a recent full
  copy of production, doing it on production too if it is quick.
- **For re-uploads, the biggest saving is to check what is already stored before inserting**
  [I]: read the stored timestamps for each sensor and chunk, and send only new values. pyarrow
  or the pandas 1.x already in the app can do this [V for the functions]. Neither library helps
  the database on its own: the web app holds tens of MiB per 100,000-value batch, not
  gigabytes [I, from a synthetic measurement]. Moving to pandas 2.2 or later would force
  SQLAlchemy 2 [I], and pandas 3 also needs Python 3.11 [V].

The biggest uncertainty is the cause itself: no upstream bug report matches this setup, so it
is not known whether the crash comes during the upload's insert or later, when the
compression job recompresses what the upload touched [I]. The crash logs can show which process
died and when; if they do not show what used the memory, a replay on staging can
([step 1](#1-read-the-crash-evidence)).

## Question and scope

Asked by Anthony Aufdenkampe on 2026-10-25, with issue
[#769](https://github.com/WikiWatershed/monitor-my-watershed/issues/769) as the starting point:

1. Would upgrading TimescaleDB from 2.19 to the latest release solve CSV uploads crashing the
   database server (AWS EC2) through memory exhaustion?
2. How might upgrading to pandas 2 or 3 and using pyarrow complement that, to reduce memory
   during large uploads?
3. With limited funds, which steps give the most return for the effort, and what is the value
   of upgrading only to 2.21?

For the Monitor My Watershed developers, to decide whether and how to do #769 and what to change
with it. Not covered: benchmarks, any change to the production or staging servers, and a full
design of the new upload path, which belongs in a later spec.

## Terms

| Term | Meaning |
| --- | --- |
| Hypertable, chunk | TimescaleDB splits `odm2.timeseriesresultvalues` into chunks of 30 days each [V, #744] |
| Hypercore (engine) | TimescaleDB's "hybrid row-columnar storage engine"[^tsdb-docs-hypercore] [V]: new data goes into the rowstore, older chunks are compressed into the columnstore. Timescale keeps developing it, e.g. 2.27.0: "The Hypercore engine now supports a vectorized implementation of filters"[^tsdb-changelog] [V] |
| Rowstore | ordinary PostgreSQL rows, uncompressed; new data lands here [V][^tsdb-docs-hypercore] |
| Columnstore | the compressed, column-oriented form. A chunk moves into it once its whole 30-day range ended more than 7 days ago, so data up to about 37 days old can still be in the rowstore [I from #744's policy]. Data is grouped by sensor (`segmentby = 'resultid'`) and sorted by time (`orderby = 'valuedatetime'`) [V, #744] |
| Access method | PostgreSQL's pluggable layer for how a table's rows are stored on disk; the standard one is `heap`. Rowstore and columnstore are how TimescaleDB lays data out; without the TAM, both live in heap tables [I] |
| Hypercore table access method (TAM) | an experimental access method (2.18–2.21) that kept B-tree indexes over compressed rows. #744 enabled it with `SET ACCESS METHOD hypercore` [V]. Removed in 2.22.0 [V]. Not the same thing as the Hypercore engine, which continues |
| Switching back to heap | `ALTER TABLE … SET ACCESS METHOD heap`. From 2.21 the data stays compressed in the columnstore [V, PR #8341] |
| OOM killer | the Linux kernel's out-of-memory killer, which ends a process when memory and swap run out [V][^pg17-overcommit] |
| Staging | a separate database server holding a very recent full copy of production [V, Anthony Aufdenkampe, 2026-10-25] |

## The system today

| Fact | Value | Source |
| --- | --- | --- |
| TimescaleDB, PostgreSQL | 2.19 on PostgreSQL 17, in production since 2025-05-01 | #740, #744, #769[^mmw-issues] [V] |
| Database and web app hosts | separate servers | [deployment guide](../deployment_guide.md) [V] |
| Database server size | 6 CPU, 16 GB RAM in 2018 notes; current size not recorded | LimnoTech's private config wiki, "Server Architecture"[^config-wiki] [U for today] |
| Table | `odm2.timeseriesresultvalues`: a PRIMARY KEY on (`resultid`, `valuedatetime`) and a second, separate UNIQUE index on the same two columns | #744[^mmw-issues] [V] |
| Storage | Hypercore engine: 30-day chunks; columnstore with `segmentby = 'resultid'`, `orderby = 'valuedatetime'`; columnstore policy after 7 days; Hypercore TAM enabled | #744 [V] |
| Staging | a staging database server with a very recent full copy of production | Anthony Aufdenkampe, 2026-10-25 [V that the requester said so] |
| Size | more than 1 billion values; 10–15 million added a month (#740, opened 2025-03-18), more than 15 million (#744, opened a week later); this document needs only the order of magnitude | #740, #744[^mmw-issues] [V] |
| Upload parse | Python `csv.reader`, row by row; values held as Python objects; rows whose first cell starts with a header label are skipped wherever they appear | `views.py` lines 312–314, 419–456[^upload-code] [V] |
| Upload timestamps | shifted to UTC before storing: `measurement_datetime.replace(tzinfo=None) - timedelta(hours=utc_offset)`, the offset read from the file's `Date and Time in UTC±N` header | `views.py` lines 353–357, 432–434[^upload-code] [V] |
| Upload write | every >100,000 values, one transaction on its own pooled connection: `CREATE TEMPORARY TABLE upload`, `copy_from`, then `INSERT INTO odm2.timeseriesresultvalues … (SELECT * FROM upload) ON CONFLICT DO NOTHING` | `views.py` lines 458–466, 1116–1153[^upload-code] [V] |
| Upload execution | synchronously, inside the web request | `views.py` lines 364–503[^upload-code] [V] |
| Database connections from the time-series code | a SQLAlchemy pool of 10 per web worker process (`pool_size=10`) | `views.py` line 54[^upload-code] [V] |
| Python pins | `python >=3.10.4`, `pandas < 2.0`, `sqlalchemy >=1.4.0,<2.0`, `django<4.0` | `environment.yml`[^upload-code] [V] |

A historical upload lands almost entirely in chunks older than 7 days, which are already in the
columnstore [I]. A re-upload of a logger's SD-card file also repeats values the logger already
streamed, so many rows conflict and are dropped by `ON CONFLICT DO NOTHING` [I].

## Where the memory goes

| Place | What holds memory | Size | Source |
| --- | --- | --- | --- |
| Web server | one flush batch, rebuilt synthetically (8 sensors, Python 3.13): 100,008 values as Python objects, plus the COPY text | 22.6 MiB for the objects (237 B/value); 29.3 MiB peak with the COPY buffer; COPY text 5.5 MiB (58 B/value) | `batch_memory.py` [I] |
| Web server | the same batch as typed columns | 2.7 MiB (28 B/value) | `batch_memory.py`, calculated [I] |
| Database | the temporary table `upload` | session-local buffers up to `temp_buffers` (default 8 MB) [V]; beyond that, local buffers are evicted to temporary files [I] | PostgreSQL 17 docs[^pg17-resource] |
| Database | conflict checks against chunks in the columnstore, without the TAM | each candidate compressed batch is decompressed in memory, tested, and reset before the next; with `DO NOTHING` nothing is moved into the rowstore | `compression_dml.c` lines 504–548 at 2.19.3[^tsdb-dml] [V]; "transient, one batch at a time" [I] |
| Database | the decompression cap `timescaledb.max_tuples_decompressed_per_dml_transaction` (default 100,000) | counts only rows moved into the rowstore (line 548), so it never fires for this `DO NOTHING` insert, given `enable_dml_decompression_tuple_filtering` at its default (on) and `valuedatetime` as a key column outside `segmentby` (`compression_scankey.c` lines 56–90); Timescale says it exists to protect storage | `guc.c`, `compression_dml.c` at 2.19.3[^tsdb-2193-source][^tsdb-dml] [V]; troubleshooting page[^tsdb-docs-troubleshooting] [V] |
| Database | conflict checks under the Hypercore TAM (production today) | the compressed-batch step is skipped (`if (!cis->use_tam)`); the check probes the unique indexes instead | `chunk_dispatch.c` line 442 at 2.19.3[^tsdb-dispatch] [V]; consequence [I] |
| Database | recompressing chunks that the upload touched | the 7-day policy job. For chunks under the TAM, `compress_chunk` goes through `tsl_compress_chunk_wrapper` to the row compressor, whose flush leaked memory in 2.19: "causing memory leaks in the ExprContext memory context. This in turn would cause problems with recompression when there were a lot of small batches" (fixed in 2.20.0, #8074). Its sorts are bounded by `maintenance_work_mem` | `compression/api.c` lines 846–873, `compression.c` lines 485, 578, 875, 902 at 2.19.3[^tsdb-2193-source]; PR #8074[^tsdb-pr8074] [V]; that the policy takes this path and that the leak matters here [I] |
| Database | the settings people usually tune | `work_mem` (per sort or hash, default 4 MB), `shared_buffers`, `temp_buffers` [V] do not bound TimescaleDB's decompression allocations [I] | PostgreSQL 17 docs[^pg17-resource] |

The web server is not where gigabytes go [I]. On the database side, desk research cannot say
which place fails:

- **Bugs fixed before 2.19 are ruled out.** An insert from a temporary table into a
  compressed hypertable was killed for running out of memory on 2.8.0 (#4903), fixed in 2.9.0
  (PR #4931). A leak in compressed-insert batch filtering was fixed in 2.17.0 (#7270).
  [^tsdb-issues] [V]
- **No report matches this setup.** No issue in the TimescaleDB tracker reports running out of
  memory on inserts into a table using the Hypercore TAM. Keyword search only, so this is not
  proof.[^tsdb-issues] [V for the searches]
- **The TAM's cache of decompressed data is not a likely cause.** It holds up to 25,000 entries
  (`hypercore_arrow_cache_max_entries`) but belongs to one tuple slot, which PostgreSQL frees
  after each uniqueness check, so on this reading it does not grow across rows. `arrow_tts.c`
  lines 120 and 144 at 2.19.3.[^tsdb-2193-source] [I]

Two candidates remain [I]. One is memory that grows during the upload's insert. The other is
the compression job that runs after it, which must recompress every chunk the upload touched
and, on 2.19, carries the #8074 leak. Timescale's troubleshooting page also warns of running
out of memory when the columnstore policy has a large backlog of chunks to move into the
columnstore.[^tsdb-docs-troubleshooting] [V] The size of the #8074 leak per batch is not stated in
any source found [U].

## Question 1: would upgrading TimescaleDB solve it?

### What the upgrade requires

| Step | Detail | Source |
| --- | --- | --- |
| Latest release | 2.31.0, 2026-10-20 | GitHub releases, CHANGELOG[^tsdb-changelog] [V] |
| PostgreSQL 17 minor needed | 17.2 or newer at 2.21.4, 2.22.0 and 2.30.2 (checked; other 2.21–2.30 releases presumably the same [I]); 17.3 or newer at 2.31.0 | `src/compat/compat.h` (`version >= 170002`; `version >= 170003` at 2.31.0)[^tsdb-compat] [V] |
| Hypercore TAM status | deprecated in 2.21.0, removed in 2.22.0: "Hypercore TAM was an experiment and it did not show the performance improvements we hoped for. … Upgrades to 2.22.0 and higher are blocked if TAM is still in use." | CHANGELOG, 2.21.0 and 2.22.0[^tsdb-changelog] [V] |
| How the block works | the 2.21→2.22 update script raises an exception if any table uses the `hypercore` access method, so `ALTER EXTENSION timescaledb UPDATE` fails | `sql/updates/2.21.3--2.22.0.sql`[^tsdb-update-script] [V]; that the update stops at the old version [I] |
| Switching back to heap | `ALTER TABLE … SET ACCESS METHOD heap` for each table using the TAM (a loop is given in the release notes) | CHANGELOG 2.21.0 and 2.22.0; PR #8341[^tsdb-pr8341] [V] |
| Where to switch | on 2.21.x. From 2.21.0 (PR #8341) the switch leaves data in the columnstore, rewrites none of it and rebuilds only indexes [V]. Before it, switching decompressed the data into the rowstore and dropped the compressed copy [I, from the code comment quoted in the PR review: "we (currently) delete the compressed chunk when changing the table access method back to 'heap'"] | PR #8341 body and review[^tsdb-pr8341]; the ordering [I] |
| Path from 2.19 | 2.19 → 2.21.4 → switch to heap → (later) 2.31.0 | [I] from the rows above |
| Minor-version mechanics | in place; `psql -X`, `ALTER EXTENSION timescaledb UPDATE TO '<version>'`; back up first; TimescaleDB and PostgreSQL cannot be upgraded in the same step | Timescale docs[^tsdb-docs-upgrade] [V] |
| One-off cautions on the way | 2.24.0 disables bloom-filter sparse indexes on chunks compressed before it (likely nothing to act on here: no bloom indexes are built for this table, see below [I]); 2.31.0 renames `timescaledb.enable_columnarscan` | CHANGELOG[^tsdb-changelog] [V] |

Each version's `.so` library is versioned, so stepping to 2.21.x probably means installing that
release's package alongside the newer one [U]. How long the switch takes on a billion-row table
is not documented [U]; staging, a recent full copy, can measure it.

### Moving off the Hypercore TAM

**Timeline** [V, CHANGELOG[^tsdb-changelog]; #744[^mmw-issues]]:

| Date | Event |
| --- | --- |
| 2025-01-23 | TimescaleDB 2.18.0 introduces the Hypercore TAM |
| 2025-05-01 | Production enables it (#744), with TimescaleDB 2.19 |
| 2025-07-08 | 2.21.0 deprecates it, warns when a table is set to use it (#8196), and adds the fast switch back to heap (#8341) |
| 2025-09-02 | 2.22.0 removes it (#8364) |
| 2025-09-25 | 2.21.4, the last 2.21 release |

**Why Timescale dropped it.** "We learned that btrees were not the right architecture", and the
columnstore is now "close to or on par with TAM without needing to store an additional index"
(CHANGELOG 2.22.0).[^tsdb-changelog] [V]

**What the switch keeps and what it changes.** The rest of the #744 configuration is columnstore
configuration, not access-method configuration: the 30-day chunks, `segmentby = 'resultid'`,
`orderby = 'valuedatetime'`, the 7-day columnstore policy, the primary key and the
de-duplicated data [I]. From 2.21 the switch leaves data in the columnstore and rewrites none of
it [V, PR #8341], so that work stays in place [I]. What goes is the unique index's coverage of
compressed rows: without the TAM, uniqueness against compressed data is checked through the
`segmentby` and min/max path described [above](#where-the-memory-goes) [I, from the 2.19.3
code]. The gains reported in #744 (about half the CPU on the database server, "similar
improvements" in RAM use, faster device posts, CSV downloads about 4.5 times faster) followed
the whole upgrade from 2.7 to 2.19, PostgreSQL 17 and the reconfiguration together; no
measurement separates the TAM's share [V for the report; I for the attribution].

**Locks.** `ALTER TABLE` takes an ACCESS EXCLUSIVE lock "unless explicitly noted", and
`SET ACCESS METHOD` is not noted otherwise[^pg17-alter-table] [V], so each relation is locked
while it switches. The release notes' loop runs inside one `DO` block, a single transaction,
so it holds every lock until it ends, and inserts into the table, including device posts, wait
for the whole run [I]. Switching one chunk per transaction keeps each lock short [I]; whether
the hypertable itself should be switched before or after its chunks is not documented [U].

**Steps, on staging first** (staging is a recent full copy, so its timings carry over)
[V for each command's source; I for the sequence]:

1. Confirm PostgreSQL 17 is at 17.2 or newer (`SELECT version();`), and make sure a current
   backup or snapshot exists.
2. Install the 2.21.4 package and run `psql -X -c "ALTER EXTENSION timescaledb UPDATE TO '2.21.4';"`.[^tsdb-docs-upgrade]
   Stopping here keeps the TAM, which 2.21.4 still supports.
3. Record `SELECT is_compressed, count(*) FROM timescaledb_information.chunks WHERE
   hypertable_schema = 'odm2' AND hypertable_name = 'timeseriesresultvalues' GROUP BY 1;`.
   Pause the columnstore policy for the duration with `SELECT alter_job(<job_id>, scheduled =>
   false);`, finding the job with `SELECT job_id FROM timescaledb_information.jobs WHERE
   hypertable_name = 'timeseriesresultvalues' AND proc_name = 'policy_compression';` (the job's
   name changes from "Compression Policy" to "Columnstore Policy" in the 2.20.0 update, so filter
   on the procedure, not the name). The pause is a precaution, not a documented requirement
   [I].[^tsdb-views][^tsdb-update-2200]
4. Switch each relation that uses the TAM to heap, one per transaction: have psql generate one
   `ALTER TABLE … SET ACCESS METHOD heap;` per relation from the release notes' query
   (`pg_class` joined to `pg_am` where `amname = 'hypercore'`) and run them in autocommit mode
   [I].[^tsdb-changelog] Time it, and watch what waits on its locks (`pg_stat_activity`).
5. Check the result:
   - no relation still uses the TAM: `SELECT count(*) FROM pg_class c JOIN pg_am a ON a.oid =
     c.relam WHERE a.amname = 'hypercore';` returns 0 [I];
   - the columnstore settings survived: `SELECT * FROM
     timescaledb_information.hypertable_compression_settings WHERE hypertable =
     'odm2.timeseriesresultvalues'::regclass;` shows `segmentby` `resultid` and `orderby`
     `valuedatetime`[^tsdb-views] [I for the expected result];
   - chunks are still compressed: `SELECT is_compressed, count(*) FROM
     timescaledb_information.chunks WHERE hypertable_schema = 'odm2' AND hypertable_name =
     'timeseriesresultvalues' GROUP BY 1;` matches the count recorded in step 3 [I];
   - note how long step 4 took and what it blocked.
6. Resume the policy (`scheduled => true`).
7. If staging's timing and blocking are acceptable, repeat steps 1–6 on production.

### What the upgrade would change for uploads

| Change | Version | Effect on this table | Source |
| --- | --- | --- | --- |
| "Fix memory leak in row compressor flush" (#8074) | 2.20.0 | removes a leak on the path that recompresses chunks after an upload, including chunks under the TAM | CHANGELOG; PR #8074; `compression/api.c` at 2.19.3[^tsdb-changelog][^tsdb-pr8074][^tsdb-2193-source] [V]; that it matters here [I] |
| Switch from the TAM to heap | migration | inserts go through the columnstore's standard conflict check (in-memory batch tests, above); production returns to a supported, maintained code path | `chunk_dispatch.c`, `compression_dml.c`[^tsdb-dispatch][^tsdb-dml] [V]; effect [I] |
| Vectorised constraint checks on backfill (#7972) | 2.20.0 | "up to 10x faster" upserts; the blog's test is 3,000 rows, all conflicting, 17 s → 1.7 s. Only after the switch: 2.21.4 still skips this step under the TAM (`chunk_dispatch.c` line 393) | CHANGELOG; 2.20 blog; `chunk_dispatch.c` at 2.21.4[^tsdb-changelog][^blog-220][^tsdb-dispatch] [V]; no memory claim |
| Cached scan keys for repeated upserts into one compressed chunk (#8182) | 2.21.0 | 1.7 s → 0.7 s on the same test; only after the switch, as above | CHANGELOG; 2.21 blog[^tsdb-changelog][^blog-221] [V]; no memory claim |
| "Fix memory leak in ColumnarScan" (#9455) | 2.26.1 | the read path: CSV downloads, and the read query in [step 6](#6-check-what-is-already-stored-before-inserting) | CHANGELOG[^tsdb-changelog] [V]; relevance [I] |
| In-memory recompression (#8569) | 2.24.0, extended in 2.25.0 and 2.30.0 | on by default (`timescaledb.enable_in_memory_recompression`, boot value `true`); "4-5x" faster recompression. Its peak memory on a 30-day chunk is not documented [U], which matters in a memory-crash document; the setting is the off switch | CHANGELOG; 2.31.0 `guc.c` line 1202[^tsdb-changelog][^tsdb-2310-source] [V] |
| `move_to_columnstore()` (#10632) with `timescaledb.move_to_columnstore_tuple_sort_limit` ("limits how many tuples `move_to_columnstore()` sorts at once to bound memory usage"; default 0, no limit) | 2.31.0 | an incremental, interruptible alternative to `compress_chunk` that takes a lock which "does not conflict with the RowExclusiveLock of INSERT, UPDATE and DELETE". The 7-day policy still calls `compress_chunk`; the function is in the internal `_timescaledb_functions` schema, so it is a tool for an operator recompressing backfilled chunks by hand or from a custom job, and may change between releases | CHANGELOG; PR #10632; `sql/policy_internal.sql` line 211, `sql/maintenance_utils.sql` line 67, `compression.c` line 3781 at 2.31.0[^tsdb-changelog][^tsdb-pr10632][^tsdb-2310-source] [V]; use and stability [I] |
| Bloom filters prune upsert decompression (#9374) | 2.26.0/2.27.0 | probably none: the defaults build no bloom filter for a key of a `segmentby` column plus a timestamp `orderby` column | CHANGELOG; `tsl/src/compression/create.c` at 2.31.0[^tsdb-changelog][^tsdb-2310-source] [V for the code]; effect [I] |
| "Direct compress" for inserts, with its own memory fixes (#10119 in 2.29.0) | 2.21 onward | none: disabled for tables with a primary key or unique index | `src/nodes/modify_hypertable.c` line 60 (INSERT) and `src/copy.c` lines 843–846 (COPY) at 2.31.0[^tsdb-2310-source] [V] |

### The value of stopping at 2.21

| Option | Gains | Leaves out |
| --- | --- | --- |
| 2.21.4, still using the TAM | the #8074 leak fix [V]; one TAM fix, #8067 "Make sure hypercore TAM parent is vacuumed" [V] | the faster conflict checks (#7972, #8182), which 2.21.4 skips under the TAM [V for the code; I for the effect]; stays on an access method that 2.21 deprecates and 2.22 removes [V] |
| 2.21.4 + switch to heap | the #8074 fix; the 2.20–2.21 conflict-check speedups; a supported access method; later upgrades become routine `ALTER EXTENSION` steps [I] | #9455 (read-path leak, 2.26.1), in-memory recompression (2.24), `move_to_columnstore()` (2.31) [V]; no further fixes, since 2.21.4 (2025-09-25) is the last 2.21 release [V for the date; I for the consequence] |

Sources: CHANGELOG[^tsdb-changelog]; `chunk_dispatch.c` at 2.21.4[^tsdb-dispatch]; PR #8341[^tsdb-pr8341].

**Answer:** upgrading alone is not shown to stop the crashes [I]. It removes a known leak in
recompression [V], but no release note claims lower memory for the insert itself [V]. It is
still worth doing: staying on 2.19 leaves production on an access method TimescaleDB has
removed [V], and 2.21.4 with the switch to heap captures most of the upgrade's value for uploads
[I].

## Question 2: what pandas 2/3 and pyarrow can add

| Option | Memory on the web server | Effect on the database | Cost to adopt | Source |
| --- | --- | --- | --- | --- |
| Keep `csv.reader` | ~30 MiB per batch | none | none | `batch_memory.py` [I] |
| `pandas.read_csv(engine="pyarrow")` | **higher**: reads the whole file into one Arrow table, then a DataFrame; `chunksize` and `iterator` are rejected | none | pandas upgrade (below) | pandas `readers.py` at 3.1.0 lines 377, 382[^pandas-readers] [V]; memory [I] |
| `pandas.read_csv(chunksize=…)` (C engine) | bounded by chunk size | none by itself | none: in pandas 1.5.3 | pandas 1.5.3 `readers.py`[^pandas-153] [V] |
| `pyarrow.csv.open_csv` (streaming) | bounded: one record batch per 1 MB block by default; single-threaded; types fixed from the first block unless given | none by itself | add pyarrow; Python 3.10 caps it at 25.0.1, the last release with Python 3.10 wheels (2026-08-10) | Arrow docs and `options.h` at 25.0.1 and 26.0.0; PyPI[^arrow-csv] [V] |
| Either, to **check what is stored and send only new values** ([step 6](#6-check-what-is-already-stored-before-inserting)) | about one chunk of data at a time | **yes**: repeated values never reach the insert | several days of code and tests | [I] |
| ADBC PostgreSQL driver (`adbc_ingest`) | Arrow batches straight to COPY | none by itself; no `ON CONFLICT` mode, so the staging table stays | new driver and connection, outside the SQLAlchemy transaction | ADBC docs, `dbapi.py`[^adbc] [V] |

**What a pandas upgrade drags in:**

| Target | Python | SQLAlchemy for `read_sql`/`to_sql` | Source |
| --- | --- | --- | --- |
| pandas 1.5.3 (current pin's newest, 2023-01-19) | ≥ 3.8 | the current pin | PyPI[^pandas-153] [V] |
| pandas 2.1.x | ≥ 3.9 | ≥ 1.4.36 (the current pin allows it; raise its floor from 1.4.0) | `_optional.py` at v2.1.4[^pandas-versions] [V] |
| pandas 2.2.0 – 2.3.3 | ≥ 3.9 | ≥ 2.0.0 | whatsnew v2.2.0 line 486; `_optional.py` at v2.3.3[^pandas-versions] [V] |
| pandas 3.0 / 3.1.0 (2026-10-22) | ≥ 3.11 | ≥ 2.0.36 / ≥ 2.0.42 | `pyproject.toml` at v3.1.0; whatsnew v3.0.0[^pandas-versions] [V] |

pandas 3 does not require pyarrow; it uses it for the new default string type when it is
installed.[^pandas-versions] [V] The app calls `read_sql` with a SQLAlchemy engine or connection
at four call sites in three files: `src/odm2/base.py` lines 102 and 104,
`src/dataloaderservices/views.py` line 1162 and `src/dataloaderinterface/ajax.py` line 60
[V, grep at `82baf4d`[^upload-code]]. So pandas ≥ 2.2 means moving to SQLAlchemy 2 [I]. Python 3.11 is past
the newest Python that Django 3.2 lists on PyPI (3.10) [V for the classifiers; whether it runs
is U]. Upgrading pandas is worth doing as tech debt, but it is not needed to fix the upload
memory problem [I].

Datetime parsing changes if the parse is vectorised. pandas 2.0 infers one format from the
first value unless `format="mixed"` or `format="ISO8601"` is given, and pandas 3.0 removes
`errors="ignore"`.[^pandas-versions] [V] The current per-row `pd.to_datetime(row[0])` is not
affected [I].

## Recommendations, in order of return on effort

Effort figures, and what each step buys, are estimates for someone who knows the servers [I].
Steps 1–3 and 5 are server work; steps 4 and 6 are code.

| Step | Effort | What it buys |
| --- | --- | --- |
| [1. Read the crash evidence](#1-read-the-crash-evidence) | an hour or two; a day if a staging replay is needed | which process dies, so the rest of the budget goes to the right cause |
| [2. Turn memory kills into failed statements](#2-turn-memory-kills-into-failed-statements) | a few hours, plus a staging test | most out-of-memory events fail one statement instead of restarting the server |
| [3. Drop the duplicate unique index](#3-drop-the-duplicate-unique-index) | an hour, plus a staging test | probably half the conflict-check and index work per inserted value |
| [4. One upload at a time, in smaller ordered statements](#4-one-upload-at-a-time-in-smaller-ordered-statements) | a day or two | no overlapping uploads; smaller statements |
| [5. Upgrade to 2.21.4 and switch to heap](#5-upgrade-to-2214-and-switch-to-heap) | several days, with staging | the #8074 fix, faster conflict checks, off the removed TAM |
| [6. Check what is already stored before inserting](#6-check-what-is-already-stored-before-inserting) | several days of code and tests | repeated values never reach the insert |
| [7. Later](#7-later) | as budget allows | 2.31, a job queue, pandas and SQLAlchemy modernisation |

Step 5 ranks above step 6 because its benefits are documented and it is needed anyway to stay
on a supported path, while step 6's saving is unmeasured and its read query is best designed
against the access method production will keep [I]. Different people can work on them at the
same time [I].

### With only 8–16 hours

All figures here are estimates [I].

| Order | Work | Hours | Notes |
| --- | --- | --- | --- |
| 1 | Step 1, the logs only (no staging replay) | 1–2 | already under way |
| 2 | Step 2, strict overcommit and the main-process OOM score, staging then production | 2–4 | worth doing whatever the logs show |
| 3 | Step 3, drop the duplicate index | about 1 | |
| 4 | Upgrade to 2.21.4 **keeping the TAM** ([steps](#moving-off-the-hypercore-tam) 1–2), staging then production, including the PostgreSQL version check, a current backup or snapshot, and installing the package | 3–6 | worth it if the logs point at the compression job (the #8074 fix); brings nothing for the insert itself, since the 2.20–2.21 conflict-check speedups are skipped under the TAM |
| 5 | On staging, time the switch to heap (steps 3–6) | 1–2 | staging is a recent full copy, so the timing carries over |
| 6 | Only if item 5 was quick and hours remain: the switch on production | 1–2 | otherwise schedule it |

Keeping the TAM on 2.21.4 is a valid interim state: 2.21.4 still supports it [V]. It postpones
the switch rather than avoiding it, because 2.22 and later refuse to install while the TAM is in
use [V], and 2.21.4 will get no further fixes [I]. If the logs instead point at the upload's
insert, spend item 4's hours on the SQL-only part of step 4 (a smaller flush size and
`ORDER BY resultid, valuedatetime`, about 2–4 hours), and leave the one-upload-at-a-time lock
for the next budget [I].

### 1. Read the crash evidence

This tells you whether crashes come during the upload's insert or later, in the compression job,
which have different fixes [I]. What to look for:

| Where | Look for | What it tells you | Source |
| --- | --- | --- | --- |
| Kernel log (`journalctl -k`, `dmesg -T` or `/var/log/kern.log`) | `Killed process <pid> (postgres)`, case-insensitive (the PostgreSQL docs show `Out of Memory: Killed process 12345 (postgres).`) | the OOM killer acted, and which process it chose | PostgreSQL 17 docs[^pg17-overcommit] [V]; log locations are Ubuntu defaults [U] |
| PostgreSQL log, same time | `<process> (PID <pid>) was terminated by signal 9: Killed`, then `Failed process was running: <SQL>` | `server process` is a client connection such as an upload; `background worker "Compression Policy [<job id>]"` is the compression job on 2.19 (renamed "Columnstore Policy" from 2.20[^tsdb-update-2200]). The SQL shows the upload's `… (select * from upload) on conflict do nothing` or a compression call | `postmaster.c` (REL_17_STABLE)[^pg17-source]; `compression_api.c` line 289 and `job.c` line 1470 at 2.19.3[^tsdb-2193-source] [V]; reading [I] |
| PostgreSQL log | `terminating any other active server processes`, then `all server processes terminated; reinitializing` | the whole-server restart users see | `postmaster.c` lines 2879, 3360[^pg17-source] [V] |
| PostgreSQL log | `out of memory` with `Failed on request of size N in memory context "…"` and a dump beginning `TopMemoryContext:` | where memory went, when an allocation failed without a kill. A kill leaves no such dump | `mcxt.c`[^pg17-source] [V]; the last sentence [I] |
| Database | `SELECT * FROM timescaledb_information.job_errors ORDER BY start_time DESC;` and `job_stats` | a row `job crash detected, see server logs` marks a job that died with the server | `sql/views.sql` at 2.19.3[^tsdb-views] [V] |
| nginx or gunicorn logs | `POST /api/data-file-upload/<id>` near each crash | crash during the request → the insert; minutes or hours later → the compression job | `urls.py`[^upload-code] [V]; reading [I] |
| Server and database | `free -h`; instance type; `SHOW shared_buffers, work_mem, maintenance_work_mem, max_connections, restart_after_crash`; `SELECT count(*) FROM pg_stat_activity`; `SELECT version()`; swap; `sysctl vm.overcommit_memory` | headroom, connection load, and the PostgreSQL 17 minor needed for step 5 | [I] |

**If the logs show which process died but not what grew**, replay one large upload on staging
and run `SELECT pg_log_backend_memory_contexts(<pid>);` on the uploading connection, and on
the compression job's worker when it runs; each call writes that process's memory contexts to
the server log [I].

### 2. Turn memory kills into failed statements

When the OOM killer ends one PostgreSQL process, "PostgreSQL will typically terminate all
remaining connections and either recover automatically, if `restart_after_crash` is enabled, or
shut down".[^pg17-overcommit] [V] PostgreSQL's documentation gives these remedies [V]; what each
does here is [I]:

| Remedy | Documented as | What it does here |
| --- | --- | --- |
| Strict overcommit: `sysctl -w vm.overcommit_memory=2`, with `vm.overcommit_ratio` set to suit the server | "will lower the chances significantly and will therefore lead to more robust system behavior" | the main fix: an allocation that would overrun memory fails with an "out of memory" error and that statement rolls back, instead of a kill that restarts the server. Any process that allocates while memory is exhausted can get the error, and a ratio set too low refuses allocations early, so test on staging |
| An OOM score of -1000 for the main postgres process (`echo -1000 > /proc/self/oom_score_adj` in the startup script, with `PG_OOM_ADJUST_FILE` and `PG_OOM_ADJUST_VALUE` so child processes stay killable) | guarantees the main process "will not be targeted by the OOM killer" | keeps the server from shutting down for good, so it recovers by itself; a killed upload connection still restarts every connection |
| More swap | the OOM killer acts only when memory and swap are both exhausted | headroom, not a fix |
| Lower `shared_buffers`, `work_mem`, `hash_mem_multiplier`; fewer connections (`max_connections`, a connection pooler) | "it may help to lower memory-related configuration parameters"; too many connections is a common cause | compare `max_connections` × `work_mem` and the web app's pools of 10 with the server's memory |

### 3. Drop the duplicate unique index

The table has both a PRIMARY KEY and a separate UNIQUE index on (`resultid`, `valuedatetime`)
[V, #744]. `ON CONFLICT DO NOTHING` with no conflict target checks every unique index, so each
value is probably checked against stored data twice, and every insert maintains two identical
indexes [I]. Dropping the extra index should roughly halve that work [I]. Check first that no
code or job refers to it by name (`timeseriesresultvalues_resultid_valuedatetime_btree_idx`
[V, #744]).

### 4. One upload at a time, in smaller ordered statements

- Let only one upload run at a time with a PostgreSQL advisory lock: take
  `pg_try_advisory_lock` on one connection held for the whole upload, and release it with
  `pg_advisory_unlock` in a `finally` block. Today each flush borrows its own pooled connection,
  so a lock taken on one of those would either stay held after it returns to the pool or end
  with the flush [I]. A second upload then gets "another upload is running, try later" [I].
- Lower the 100,000-value flush size and add `ORDER BY resultid, valuedatetime` to the
  `INSERT … SELECT`, so each statement is smaller and touches one sensor's data at a time [I].
- Optionally, cap the file size in `SensorDataForm` as a backstop [I].

### 5. Upgrade to 2.21.4 and switch to heap

Follow [Moving off the Hypercore TAM](#moving-off-the-hypercore-tam), on staging first.
Keep `max_tuples_decompressed_per_dml_transaction` at its default: setting it to 0 removes the
guard against a single statement filling the disk with decompressed rows [I]. See
[The value of stopping at 2.21](#the-value-of-stopping-at-221) for what this does and does not
buy.

### 6. Check what is already stored before inserting

Today every value goes to `INSERT … ON CONFLICT DO NOTHING`, so a re-upload of data that already
streamed in makes the database check each repeated value against stored, compressed data [I].
Reading the stored timestamps once per sensor and chunk, then sending only new values, replaces
those per-value checks with one read per sensor-chunk [I]. The read uses the `segmentby
resultid` index and the stored minimum and maximum times, so it touches each compressed batch
once [I]. One sensor's timestamps for a 30-day chunk, at 8 bytes each, are small: 2,880 values
(23 KB) at 15-minute logging, 43,200 (346 KB) at 1-minute [I, calculated]. When every value in
a window is already stored, nothing is sent for it [I]. `ON CONFLICT DO NOTHING` stays as a
safety net, because the logger may stream new values while the upload runs [I].

The steps, in both libraries. Function names are checked against pyarrow 25.0.1 and 26.0.0 and
pandas 1.5.3[^arrow-api][^pandas-153] [V]; the workflow has not been run [I].

| Step | Why | pyarrow | pandas 1.x |
| --- | --- | --- | --- |
| 1. Read the header block | the sampling feature, result UUIDs and UTC offset come from the first rows; their count varies | as `build_results_dict` does now, and note the line where data starts | same |
| 2. Drop header rows anywhere in the file | concatenated logger files repeat the header block mid-file; today's parser skips such rows wherever they appear, but a typed CSV reader would fail on them | filter lines whose first cell starts with a header label before they reach the reader (e.g. a wrapping line iterator) | same filter, or read the timestamp column as text and drop non-matching rows |
| 3. Read in pieces, with explicit types | bounded memory; a column that starts empty would otherwise get the wrong type | `pyarrow.csv.open_csv(f, read_options=ReadOptions(skip_rows=n), convert_options=ConvertOptions(column_types=…))` | `pd.read_csv(f, skiprows=n, chunksize=…, dtype=…)` |
| 4. Shift timestamps to UTC, as stored | stored `valuedatetime` is local time minus the header's UTC offset; without the same shift, nothing matches in step 9 and every value is sent | subtract the offset, as a duration, from the timestamp column | `df["ts"] - pd.Timedelta(hours=offset)` |
| 5. Take each sensor's series | the file is wide: one column per sensor (result UUID), so grouping by sensor is choosing a column | the timestamp column and one value column; `drop_null` removes empty cells | `df[["ts", col]].dropna()` |
| 6. Sort by time | usually already in order; one sort reorders all columns; the sort must be stable so step 7 keeps the file's first row | `pc.sort_indices` on the timestamps (stable), then `Table.take` | `sort_values("ts", kind="stable")` (the default sort is not stable) |
| 7. Drop repeats within the file | concatenated or restarted logger files repeat timestamps; keep the first, matching `DO NOTHING` | there is no `drop_duplicates`: compare each sorted timestamp with the one before it and filter; `group_by(...).aggregate([(col, "first")])` also works but needs `use_threads=False`, since `first` depends on input order | `drop_duplicates(subset="ts", keep="first")` |
| 8. Split by chunk | one read query and one insert per (sensor, chunk). Values outside every existing chunk (before the first, in a gap, after the last) have nothing stored to compare with: send them as they are, or the recipe drops them | chunk ranges from `SELECT range_start, range_end FROM timescaledb_information.chunks WHERE hypertable_schema = 'odm2' AND hypertable_name = 'timeseriesresultvalues'`; filter each series to each range, and collect the rest separately | same query; boolean masks on `ts` |
| 9. Read what is stored, and keep only new values | the database check, once per window that has a chunk; skip the window when nothing is left | `SELECT valuedatetime FROM odm2.timeseriesresultvalues WHERE resultid = :r AND valuedatetime >= :start AND valuedatetime < :end`; build `stored = pa.array(rows, type=ts.type)` (same unit, no time zone) and `Table.filter(pc.invert(pc.is_in(ts, value_set=stored)))` | the same query; `s[~s["ts"].isin(stored)]` |
| 10. Send them | the existing temporary table and insert, with constants (UTC offset, censor code, quality code, interval and its unit) written as literals in the SQL rather than repeated on every row | `pyarrow.csv.write_csv(t, buf, WriteOptions(include_header=False))`, then psycopg2 `copy_expert("COPY upload (…) FROM STDIN WITH (FORMAT csv)", buf)` | `df.to_csv(buf, header=False, index=False)`, then the same `copy_expert` |

Logger files are written in time order, so the work can run as the file streams in: hold record
batches (or pandas chunks) until their timestamps pass a chunk boundary, then finish that chunk
for every sensor [I]. Memory then stays at about one chunk of data [I]. A file out of time order
would need a full read first [I].

Which library: pandas 1.5.3 is already installed and does every step; pyarrow adds a streaming
reader, typed columns (about 28 B per value instead of 237 in the synthetic measurement) and
vectorised steps, at the cost of a new dependency [I]. The database saving comes from step 9,
whichever library runs it [I]. Mixed date formats within one file need a per-row fallback to
keep today's "Unrecognized date format" warnings [I].

### 7. Later

- **2.21.4 → 2.31.0.** Routine once the access method is heap; needs PostgreSQL 17.3 or newer
  [V, compat.h]. Brings #9455 and `move_to_columnstore()` [V, CHANGELOG]. It also turns on
  in-memory recompression, whose memory use is undocumented [U]; watch memory on the first
  recompressions after the upgrade, and keep `timescaledb.enable_in_memory_recompression` in
  mind as the off switch [I].
- **A job queue for uploads**, replacing step 4's lock [I].
- **pandas 2.2+, SQLAlchemy 2, a newer Django and Python 3.11**: worthwhile tech debt, but they
  do not help this problem [I].

## Limitations and uncertainties

| Factor | Direction of error | Magnitude |
| --- | --- | --- |
| No access to crash logs, server size or `postgresql.conf` | the cause may be one this document does not consider | could change the order of steps 3–6 |
| Size of the #8074 leak per batch unknown | the compression job may matter more or less than the insert | unknown |
| Insert memory under the TAM not traced to the allocation | the insert path may hold or free more than inferred | unknown |
| Memory use of in-memory recompression (2.24+) undocumented | upgrading past 2.21 could raise peak memory during recompression | unknown; watch after upgrading |
| Effort figures are estimates | steps may cost more or less | ± a factor of two [I] |
| Upgrade speedups measured by Timescale on 3,000 rows, with an explicit conflict target `ON CONFLICT (uk, ts)`; production's insert has none | real backfills of 100,000-row batches may gain more or less | unknown |
| Cost of step 6's read query against the conflict checks it replaces not measured | the saving may be smaller than expected | unknown; measure on staging |
| Dropping the duplicate index assumed to halve conflict checks | the planner may already check one index first | small to moderate |
| Bloom-filter and old-chunk behaviour read from source, not run | the upgrade might help upserts more than stated | small to moderate |
| `batch_memory.py` is a synthetic 8-sensor batch on Python 3.13 | Python 3.10 objects are likely larger, since 3.11 stopped building a full `__dict__` for each instance [I] | not measured; still tens of MiB per batch [I] |

## Open questions

| Question | What would settle it | Who |
| --- | --- | --- |
| Which process dies during a crash, and when? | [Step 1](#1-read-the-crash-evidence) | Paul Tomasula (has started on the logs) |
| How much memory does the #8074 leak cost per batch? [U] | A staging replay with `pg_log_backend_memory_contexts` on the compression job's worker | MMW developers |
| Does in-memory recompression raise peak memory when recompressing a backfilled 30-day chunk? [U] | A staging recompression on 2.24+ with memory-context logging, or the 2.31 source | MMW developers |
| Current database server size and memory settings [U] | Step 1's baseline commands and the EC2 instance type | MMW developers |
| Exact PostgreSQL 17 minor on production [U] | `SELECT version();` (≥ 17.2 for 2.21.4, ≥ 17.3 for 2.31.0) | MMW developers |
| Where do the server's logs live, and does the kernel there print a per-process memory table with OOM kills? [U] | The server's PostgreSQL `log_directory`, journald settings, and one kernel OOM message | MMW developers |
| What `vm.overcommit_ratio` suits the server? | Its RAM, swap and `shared_buffers`; a staging test | MMW developers |
| Does anything refer to the duplicate unique index by name? | A search of the code, jobs and SQL scripts | MMW developers |
| Must the 2.21.4 package be installed to step through it? [U] | Timescale's package repository for the server's OS; a dry run on staging | MMW developers |
| How long does the switch to heap take, and what does it block, on this table? [U] | [Moving off the Hypercore TAM](#moving-off-the-hypercore-tam), steps 3–6, on staging | MMW developers |
| Should the hypertable be switched before or after its chunks? [U] | Timescale's support, or a trial on staging | MMW developers |
| Does step 6's read query cost less than the conflict checks it replaces? | A timed staging upload of a mostly repeated file, with and without step 6 | MMW developers |
| Does Django 3.2 run on Python 3.11 in this stack (pyarrow ships Python 3.11 wheels)? [U] | A test environment build | MMW developers |
| Is a job queue acceptable on the web server? | Team decision | Anthony Aufdenkampe, Paul Tomasula |

## Appendix: revision history

| Revision | Date | Changes |
| --- | --- | --- |
| 1 | 2026-10-25 | First version. |
| 2 | 2026-10-25 | After review by Anthony Aufdenkampe. **Added:** a third question (return on effort; the value of stopping at 2.21); a Terms section distinguishing the Hypercore engine (Timescale's hybrid row-columnar storage, the rowstore plus the columnstore) from the Hypercore table access method, with all statements about "Hypercore" made specific to one or the other, and defining the OOM killer and staging; a section on moving off the TAM (timeline, why Timescale dropped it, what the switch keeps, the locks it takes, steps on staging switching one chunk per transaction, and checks); a table on stopping at 2.21, and a plan for 8–16 hours of work, including upgrading to 2.21.4 while keeping the TAM; the finding that the 2.20–2.21 conflict-check speedups apply only after the switch; the fact that staging is a recent full copy of production; Recommendations reordered by return on effort, with new steps for the crash-log checklist, strict memory overcommit and the duplicate unique index; detailed steps, in pyarrow and pandas 1.x, for checking stored values before inserting, including the UTC-offset shift and mid-file header rows. **Changed:** #8074 (2.20.0) is now identified as a memory-leak fix on the path that recompresses chunks after an upload, where Revision 1 treated its relevance as uncertain; the Summary now answers Question 1 directly; `move_to_columnstore()` (2.31.0) is described as an operator tool for recompressing backfilled chunks; in-memory recompression (2.24+) is flagged as on by default with undocumented memory use; `batch_memory.py` results are marked [I], as a synthetic measurement. Running uploads off the web request in a job queue, Revision 1's lead lever, moved to "Later": an advisory lock achieves one upload at a time sooner and more cheaply. **Removed:** Revision 1's recommendation to backfill with Timescale's `convert_to_rowstore`/insert/`convert_to_columnstore` procedure, its cautions and the issue #8775 citation, and the open question on that procedure, because the docs page is tagged "Old API" and converting a whole 30-day chunk is costly, while the cheaper steps now come first; the separate staging-replay recommendation, now folded into step 1; the pandas IO-guide reference, no longer cited. |

## References

[^mmw-issues]: WikiWatershed. monitor-my-watershed issues
    [#740](https://github.com/WikiWatershed/monitor-my-watershed/issues/740) (TimescaleDB and
    PostgreSQL upgrade, comments to 2025-05-01),
    [#744](https://github.com/WikiWatershed/monitor-my-watershed/issues/744) (Hypercore TAM and
    columnstore configuration SQL, comment by ptomasula, 2025-05-01; results comment by
    aufdenkampe, 2025-09-24) and
    [#769](https://github.com/WikiWatershed/monitor-my-watershed/issues/769). Read with
    `gh issue view`. Accessed 2026-10-25.
[^upload-code]: WikiWatershed. `src/dataloaderservices/views.py`, `src/dataloaderservices/urls.py`
    and `environment.yml`, commit `82baf4d`.
    https://github.com/WikiWatershed/monitor-my-watershed/blob/82baf4d/src/dataloaderservices/views.py
    Accessed 2026-10-25.
[^config-wiki]: LimnoTech. ODM2DataSharingPortalConfig wiki, "Server Architecture" (private;
    last edited 2022). Accessed 2026-10-25.
[^pg17-resource]: PostgreSQL Global Development Group. *PostgreSQL 17 documentation, 19.4
    Resource Consumption* (`work_mem`, `maintenance_work_mem`, `temp_buffers`,
    `shared_buffers`). https://www.postgresql.org/docs/17/runtime-config-resource.html ; read as
    `doc/src/sgml/config.sgml` on `REL_17_STABLE`. Accessed 2026-10-25.
[^pg17-overcommit]: PostgreSQL Global Development Group. *PostgreSQL 17 documentation, 18.4.4
    Linux Memory Overcommit*. https://www.postgresql.org/docs/17/kernel-resources.html#LINUX-MEMORY-OVERCOMMIT ;
    read as `doc/src/sgml/runtime.sgml` on `REL_17_STABLE`. Accessed 2026-10-25.
[^pg17-alter-table]: PostgreSQL Global Development Group. *PostgreSQL 17 documentation, ALTER
    TABLE* ("An ACCESS EXCLUSIVE lock is acquired unless explicitly noted"; `SET ACCESS METHOD`).
    https://www.postgresql.org/docs/17/sql-altertable.html ; read as
    `doc/src/sgml/ref/alter_table.sgml` on `REL_17_STABLE`. Accessed 2026-10-25.
[^pg17-source]: PostgreSQL Global Development Group. `src/backend/postmaster/postmaster.c`
    (lines 2879, 3088, 3360) and `src/backend/utils/mmgr/mcxt.c` (lines 353, 1160–1161) on
    `REL_17_STABLE`. https://github.com/postgres/postgres/tree/REL_17_STABLE Accessed 2026-10-25.
[^tsdb-changelog]: Timescale. *TimescaleDB CHANGELOG*, `main` (top entry 2.31.0, 2026-10-20).
    https://github.com/timescale/timescaledb/blob/main/CHANGELOG.md Accessed 2026-10-25.
[^tsdb-2193-source]: Timescale. TimescaleDB 2.19.3 source: `src/guc.c`
    (`max_tuples_decompressed_per_dml_transaction`, `hypercore_arrow_cache_max_entries`,
    `enable_dml_decompression_tuple_filtering` at lines 591–596), `src/bgw/job.c` (line 1470,
    job names `"%s [%d]"`), `tsl/src/hypercore/arrow_cache.c`, `tsl/src/hypercore/arrow_tts.c`,
    `tsl/src/compression/api.c` (lines 846–873), `tsl/src/compression/compression.c` (lines 485,
    578, 875, 902), `tsl/src/compression/recompress.c` (lines 285, 300, 694),
    `tsl/src/bgw_policy/compression_api.c` (line 289).
    https://github.com/timescale/timescaledb/tree/2.19.3 Accessed 2026-10-25.
[^tsdb-2310-source]: Timescale. TimescaleDB 2.31.0 source: `src/guc.c` (line 1202,
    `enable_in_memory_recompression`), `sql/policy_internal.sql` (line 211, `compress_chunk`),
    `sql/maintenance_utils.sql` (line 67, `move_to_columnstore`),
    `tsl/src/compression/compression.c` (line 3781, the only read of
    `move_to_columnstore_tuple_sort_limit`), `tsl/src/compression/create.c`
    (`create_default_composite_bloom`; `should_create_bloom_sparse_index`, line 420),
    `src/nodes/modify_hypertable.c` (line 60), `src/copy.c` (lines 843–846).
    https://github.com/timescale/timescaledb/tree/2.31.0 Accessed 2026-10-25.
[^tsdb-dml]: Timescale. TimescaleDB 2.19.3, `tsl/src/compression/compression_dml.c`,
    `decompress_batches_scan` (lines 504–548) and `batch_matches` (lines 590–621); and
    `tsl/src/compression/compression_scankey.c` (lines 56–90).
    https://github.com/timescale/timescaledb/blob/2.19.3/tsl/src/compression/compression_dml.c
    https://github.com/timescale/timescaledb/blob/2.19.3/tsl/src/compression/compression_scankey.c
    Accessed 2026-10-25.
[^tsdb-dispatch]: Timescale. `src/nodes/chunk_dispatch/chunk_dispatch.c` at 2.19.3 (line 442)
    and 2.21.4 (line 393). https://github.com/timescale/timescaledb/blob/2.19.3/src/nodes/chunk_dispatch/chunk_dispatch.c#L442
    Accessed 2026-10-25.
[^tsdb-views]: Timescale. `sql/views.sql` at 2.19.3 and 2.21.4 (`timescaledb_information.jobs`,
    `job_stats`, `job_errors`, `chunks`, `hypertable_compression_settings`).
    https://github.com/timescale/timescaledb/blob/2.21.4/sql/views.sql Accessed 2026-10-25.
[^tsdb-issues]: Timescale. timescaledb issues
    [#4903](https://github.com/timescale/timescaledb/issues/4903) and PR
    [#4931](https://github.com/timescale/timescaledb/pull/4931);
    [#7270](https://github.com/timescale/timescaledb/pull/7270); issue search for memory and
    out-of-memory reports on compressed inserts and the Hypercore TAM (queries in the research
    log). Accessed 2026-10-25.
[^tsdb-pr8074]: Timescale. PR #8074, "Use correct memory context during flush", merged
    2025-05-08. https://github.com/timescale/timescaledb/pull/8074 Accessed 2026-10-25.
[^tsdb-pr10632]: Timescale. PR #10632, "Move chunk rows to columnstore as DML", merged
    2026-09-25. https://github.com/timescale/timescaledb/pull/10632 Accessed 2026-10-25.
[^tsdb-compat]: Timescale. TimescaleDB `src/compat/compat.h` at tags 2.21.4, 2.22.0, 2.30.2 and
    2.31.0 (lines 32–35 at 2.31.0).
    https://github.com/timescale/timescaledb/blob/2.31.0/src/compat/compat.h Accessed 2026-10-25.
[^tsdb-update-script]: Timescale. TimescaleDB 2.22.0, `sql/updates/2.21.3--2.22.0.sql`, lines
    2–9. https://github.com/timescale/timescaledb/blob/2.22.0/sql/updates/2.21.3--2.22.0.sql
    Accessed 2026-10-25.
[^tsdb-update-2200]: Timescale. TimescaleDB 2.20.0, `sql/updates/2.19.3--2.20.0.sql`, line 61
    (renames "Compression Policy" jobs to "Columnstore Policy"); the job's `proc_name` is
    `policy_compression` (`tsl/src/bgw_policy/policies_v2.h` line 26 at 2.19.3;
    `sql/policy_internal.sql` line 182 at 2.21.4).
    https://github.com/timescale/timescaledb/blob/2.20.0/sql/updates/2.19.3--2.20.0.sql
    Accessed 2026-10-25.
[^tsdb-pr8341]: Timescale. PR #8341, "Allow quick migration from hypercore TAM to (columnstore)
    heap", merged 2025-07-07, with review comments.
    https://github.com/timescale/timescaledb/pull/8341 Accessed 2026-10-25.
[^tsdb-docs-upgrade]: Timescale. Docs source, `latest` branch: `self-hosted/upgrades/minor-upgrade.md`,
    `_partials/_migrate_self_postgres_implement_migration_path.md`, `_partials/_plan_upgrade.md`.
    https://github.com/timescale/docs (archived; live site https://docs.tigerdata.com).
    Accessed 2026-10-25.
[^tsdb-docs-hypercore]: Timescale. Docs source at commit `a28536b`, `_partials/_hypercore-intro.md`
    ("a hybrid row-columnar storage engine"; "new data is initially written to the rowstore").
    https://github.com/timescale/docs/blob/a28536b21937249fbe2b9bbf642a51039369153a/_partials/_hypercore-intro.md
    (archived). Accessed 2026-10-25.
[^tsdb-docs-troubleshooting]: Timescale. Docs source at commit `a28536b`:
    `_troubleshooting/columnstore-backlog-ooms.md` and
    `_troubleshooting/compression-dml-tuple-limit.md`.
    https://github.com/timescale/docs/tree/a28536b21937249fbe2b9bbf642a51039369153a (archived).
    Accessed 2026-10-25.
[^blog-220]: Tiger Data. *Speed without sacrifice: 2500x faster distinct queries, 10x faster
    upserts, bloom filters — TimescaleDB 2.20*. https://www.tigerdata.com/blog/speed-without-sacrifice-2500x-faster-distinct-queries-10x-faster-upserts-bloom-filters-timescaledb-2-20
    Accessed 2026-10-25.
[^blog-221]: Tiger Data. *Speed without sacrifice: 37x faster high-performance ingestion, 42x
    faster deletes, improved CAGG updates — TimescaleDB 2.21*. https://www.tigerdata.com/blog/speed-without-sacrifice-37x-faster-high-performance-ingestion-42x-faster-deletes-improved-cagg-updates-timescaledb-2-21
    Accessed 2026-10-25.
[^pandas-readers]: pandas. `pandas/io/parsers/readers.py` at v3.1.0, lines 377–383.
    https://github.com/pandas-dev/pandas/blob/v3.1.0/pandas/io/parsers/readers.py Accessed 2026-10-25.
[^pandas-153]: pandas. v1.5.3 source: `pandas/io/parsers/readers.py` (`read_csv`, `skiprows`,
    `chunksize`), `pandas/core/frame.py` (`drop_duplicates(subset, keep="first")`,
    `sort_values`, `dropna`), `pandas/core/series.py` (`isin`), `pandas/core/generic.py`
    (`to_csv`); PyPI JSON (1.5.3, 2023-01-19, `requires_python >=3.8`).
    https://github.com/pandas-dev/pandas/tree/v1.5.3 Accessed 2026-10-25.
[^pandas-versions]: pandas. `pyproject.toml` at v3.1.0; `pandas/compat/_optional.py` at v2.1.4
    and v2.3.3; whatsnew v2.0.0, v2.2.0 and v3.0.0 (`doc/source/whatsnew/`); PyPI JSON for
    release dates. https://github.com/pandas-dev/pandas Accessed 2026-10-25.
[^arrow-csv]: Apache Arrow. *Reading and writing CSV files* (`docs/source/python/csv.rst`) and
    `cpp/src/arrow/csv/options.h` (line 153, `block_size = 1 << 20`) at apache-arrow-25.0.1 and
    26.0.0; PyPI JSON for pyarrow 25.0.1 and 26.0.0 (wheel tags).
    https://arrow.apache.org/docs/python/csv.html Accessed 2026-10-25.
[^arrow-api]: Apache Arrow 25.0.1 and 26.0.0: `python/pyarrow/table.pxi` (`sort_by`, `filter`,
    `take`, `drop_null`, `group_by`, `aggregate`), `docs/source/cpp/compute.rst` (`is_in`,
    `sort_indices`, `hash_first`: "Result is based on ordering of the input data"),
    `python/pyarrow/_csv.pyx` (`WriteOptions.include_header`).
    https://github.com/apache/arrow/tree/apache-arrow-25.0.1 Accessed 2026-10-25.
[^adbc]: Apache Arrow ADBC. *PostgreSQL driver* docs (`docs/source/driver/postgresql.rst`,
    `main`) and `adbc_driver_manager/dbapi.py` at apache-arrow-adbc-24.
    https://arrow.apache.org/adbc/current/driver/postgresql.html Accessed 2026-10-25.
