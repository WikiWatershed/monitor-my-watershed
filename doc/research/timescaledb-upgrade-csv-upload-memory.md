# TimescaleDB upgrade and memory exhaustion during large CSV uploads

**Revision 1, 2026-10-25.** Anthony Aufdenkampe, LimnoTech (requested the work); drafted with
Claude (Claude Code); not yet reviewed by a person. Markers: [V] checked against a cited source
opened for this work or a probe run for it; [I] derived or inferred; [U] not checked. Sources
accessed 2026-10-25. Marker density: reference.
Working record: [log, scripts](timescaledb_upgrade_csv_upload_memory/).
History: [Appendix](#appendix-revision-history).

## Summary

Large CSV uploads of historical logger data have been crashing the Monitor My Watershed
database server by exhausting its memory. Issue #769 proposes upgrading TimescaleDB from 2.19
to 2.26 or later. This document asks whether that upgrade would stop the crashes, what it would
take, and how moving the web app to pandas 2 or 3 with pyarrow could help. It is desk research:
documentation, release notes, issue trackers and source code were read, and nothing was run
against a database.

- **Upgrade, but don't expect it alone to stop the crashes.** No TimescaleDB release note from
  2.20 to 2.31 claims lower memory for the insert itself that an upload makes [V]. The
  advertised gains are about speed, measured on a 3,000-row test [V].
- **The upgrade is a migration, not a version bump.** Production stores its main data table in
  the Hypercore table access method, which TimescaleDB removed in 2.22.0. Upgrades past 2.21 are
  refused until every table is converted back to standard (heap) storage [V]. From 2.21 the
  conversion avoids rewriting the data [V], and before 2.21 it appears not to [I], so the path
  is 2.19 → 2.21 → convert → 2.31 [I].
- **The bigger lever is how uploads reach the database** [I]. Run uploads one at a time off the
  web request, send rows sorted and grouped by sensor and month, and load very large historical
  files the way Timescale documents for backfills, after the migration.
- **pandas or pyarrow on its own does not help the database** [I]. The web app holds about
  30 MiB per 100,000-value batch [V], and the same SQL reaches the database whatever parses the
  file. Their value is cheap sorting, de-duplication and streaming. pyarrow's streaming reader
  does this without a pandas upgrade [I]. pandas 2.2 or later requires SQLAlchemy 2 for
  `read_sql` [V], which the app uses, so it would force SQLAlchemy 2 [I]; pandas 3 also needs
  Python 3.11 [V].

The tightest margin is the cause itself: no upstream bug report matches this setup, so the
mechanism behind the crash is unknown [V for the search; I for the conclusion]. The cheapest
next step is to read the database server's logs from a crash and to measure one upload on a
staging copy (see [Open questions](#open-questions)).

## Question and scope

Asked by Anthony Aufdenkampe on 2026-10-25, with issue
[#769](https://github.com/WikiWatershed/monitor-my-watershed/issues/769) as the starting point:

1. Would upgrading TimescaleDB from 2.19 to the latest release solve CSV uploads crashing the
   database server (AWS EC2) through memory exhaustion?
2. How might upgrading to pandas 2 or 3 and using pyarrow complement that, to reduce memory
   during large uploads?

For the Monitor My Watershed developers, to decide whether and how to do #769 and what to change
with it. Not covered: benchmarks, any change to the production or staging servers, and a design
of the new upload path, which belongs in a later spec.

## The system today

| Fact | Value | Source |
| --- | --- | --- |
| TimescaleDB, PostgreSQL | 2.19 on PostgreSQL 17, in production since 2025-05-01 | #740, #744, #769[^mmw-issues] [V] |
| Database and web app hosts | separate servers | [deployment guide](../deployment_guide.md) [V] |
| Database server size | 6 CPU, 16 GB RAM in 2018 notes; current size not recorded | private config wiki, "Server Architecture"[^config-wiki] [U for today] |
| Table | `odm2.timeseriesresultvalues`, PRIMARY KEY and a unique index on (`resultid`, `valuedatetime`) | #744[^mmw-issues] [V] |
| Hypertable chunks | 30 days on `valuedatetime` | #744 [V] |
| Storage | `SET ACCESS METHOD hypercore`; columnstore `segmentby = 'resultid'`, `orderby = 'valuedatetime'` | #744 [V] |
| Columnstore policy | chunks move to the columnstore after 7 days | #744 [V] |
| Size | more than 1 billion values; 10–15 million added a month (#740, opened 2025-03-18), more than 15 million (#744, opened a week later); this document needs only the order of magnitude | #740, #744[^mmw-issues] [V] |
| Upload parse | Python `csv.reader`, row by row; values held as Python objects | `views.py` lines 419–456[^upload-code] [V] |
| Upload write | every >100,000 values, one transaction: `CREATE TEMPORARY TABLE upload`, `copy_from`, then `INSERT INTO odm2.timeseriesresultvalues … (SELECT * FROM upload) ON CONFLICT DO NOTHING` | `views.py` lines 458–466, 1116–1153[^upload-code] [V] |
| Upload execution | synchronously, inside the web request | `views.py` lines 364–503[^upload-code] [V] |
| Python pins | `python >=3.10.4`, `pandas < 2.0`, `sqlalchemy >=1.4.0,<2.0`, `django<4.0` | `environment.yml`[^upload-code] [V] |

A historical upload lands almost entirely in chunks older than 7 days, which are already in the
columnstore [I]. A re-upload of a logger's SD-card file also repeats values the logger already
streamed, so many rows conflict and are dropped by `ON CONFLICT DO NOTHING` [I].

## Where the memory goes

| Place | What holds memory | Size | Source |
| --- | --- | --- | --- |
| Web server | one flush batch: 100,008 values as Python objects, plus the COPY text | 22.6 MiB for the objects (237 B/value); 29.3 MiB peak with the COPY buffer; COPY text 5.5 MiB (58 B/value) | `batch_memory.py`, Python 3.13.15 [V] |
| Web server | the same batch as typed columns | 2.7 MiB (28 B/value) | `batch_memory.py`, calculated [I] |
| Database | the temporary table `upload` | session-local buffers up to `temp_buffers` (default 8 MB) [V]; beyond that, local buffers are evicted to temporary files [I] | PostgreSQL 17 docs[^pg17-resource] |
| Database | conflict checks on standard (heap) columnstore chunks | each candidate compressed batch is decompressed in memory, tested, and reset before the next; with `DO NOTHING` nothing is moved into the rowstore | `compression_dml.c` lines 504–548 at 2.19.3[^tsdb-dml] [V]; "transient, one batch at a time" [I] |
| Database | the decompression cap `timescaledb.max_tuples_decompressed_per_dml_transaction` (default 100,000) | counts only rows moved into the rowstore (line 548), so it never fires for this `DO NOTHING` insert, given `enable_dml_decompression_tuple_filtering` at its default (on) and `valuedatetime` as a key column outside `segmentby` (`compression_scankey.c` lines 56–90); Timescale says it exists to protect storage | `guc.c`, `compression_dml.c` at 2.19.3[^tsdb-guc][^tsdb-dml] [V]; troubleshooting page[^tsdb-docs-backfill] [V] |
| Database | conflict checks on Hypercore chunks (production today) | the compressed-batch step is skipped (`if (!cis->use_tam)`); the check probes the unique index instead | `chunk_dispatch.c` line 442 at 2.19.3[^tsdb-dispatch] [V]; consequence [I] |
| Database | compressing chunks that the upload touched | the 7-day policy job; its sorts are bounded by `maintenance_work_mem` | `compression.c` line 578 and `recompress.c` lines 285, 300 at 2.19.3[^tsdb-guc] [V] |
| Database | the settings people usually tune | `work_mem` (per sort or hash, default 4 MB), `shared_buffers`, `temp_buffers` [V] do not bound TimescaleDB's decompression allocations [I] | PostgreSQL 17 docs[^pg17-resource] |

The web server is not where gigabytes go [I]. On the database side, desk research cannot say
which of the remaining places fails, for three reasons:

- **The known bugs are already fixed in 2.19.** An insert from a temporary table into a
  compressed hypertable was killed for running out of memory on 2.8.0 (#4903), fixed in 2.9.0
  (PR #4931). A leak in compressed-insert batch filtering was fixed in 2.17.0 (#7270).
  [^tsdb-issues] [V]
- **No report matches this setup.** No issue in the TimescaleDB tracker reports running out of
  memory on inserts into a Hypercore table. Keyword search only, so this is not proof.
  [^tsdb-issues] [V for the searches]
- **The obvious suspect is ruled out.** The Hypercore cache of decompressed data, up to 25,000
  entries (`hypercore_arrow_cache_max_entries`), belongs to one tuple slot. The slot is freed
  when PostgreSQL drops it after each uniqueness check, so on this reading the cache does not
  grow across rows. `arrow_tts.c` lines 120 and 144 at 2.19.3.[^tsdb-guc] [I]

Two unchecked possibilities remain. One is memory that grows during a single upload and is not
freed. The other is that the crash comes later, from the compression job recompressing every
chunk the upload touched; Timescale's troubleshooting page warns of running out of memory with
a large compression backlog.[^tsdb-docs-backfill] [I]

## Question 1: would upgrading TimescaleDB solve it?

### What the upgrade requires

| Step | Detail | Source |
| --- | --- | --- |
| Latest release | 2.31.0, 2026-10-20 | GitHub releases, CHANGELOG[^tsdb-changelog] [V] |
| PostgreSQL 17 minor needed | 17.2 or newer for 2.21.x–2.30.x; 17.3 or newer for 2.31.0 | `src/compat/compat.h` at 2.21.4, 2.22.0, 2.30.2 (`version >= 170002`) and 2.31.0 (`version >= 170003`)[^tsdb-compat] [V] |
| Hypercore status | deprecated in 2.21.0, removed in 2.22.0: "Hypercore TAM was an experiment and it did not show the performance improvements we hoped for. … Upgrades to 2.22.0 and higher are blocked if TAM is still in use." | CHANGELOG, 2.22.0[^tsdb-changelog] [V] |
| How the block works | the 2.21→2.22 update script raises an exception if any table uses the `hypercore` access method, so `ALTER EXTENSION timescaledb UPDATE` fails | `sql/updates/2.21.3--2.22.0.sql`[^tsdb-update-script] [V]; that the update stops at the old version [I] |
| Converting back | `ALTER TABLE … SET ACCESS METHOD heap` for each Hypercore table (a loop is given in the release notes) | CHANGELOG 2.22.0; PR #8341[^tsdb-pr8341] [V] |
| Where to convert | on 2.21.x. From 2.21.0 (PR #8341) the conversion keeps data in the columnstore, rewrites no data and rebuilds only indexes [V]. Before it, converting decompressed the data into row storage and dropped the compressed copy [I, from the code comment quoted in the PR review: "we (currently) delete the compressed chunk when changing the table access method back to 'heap'"] | PR #8341 body and review[^tsdb-pr8341]; the ordering [I] |
| Path from 2.19 | 2.19 → 2.21.x → convert → 2.31.0 | [I] from the rows above |
| Minor-version mechanics | in place; `psql -X`, `ALTER EXTENSION timescaledb UPDATE TO '<version>'`; back up first; TimescaleDB and PostgreSQL cannot be upgraded in the same step | Timescale docs[^tsdb-docs-upgrade] [V] |
| One-off cautions on the way | 2.24.0 disables bloom-filter sparse indexes on chunks compressed before it (likely nothing to act on here: no bloom indexes are built for this table, see below [I]); 2.31.0 renames `timescaledb.enable_columnarscan` | CHANGELOG[^tsdb-changelog] [V] |

Each version's `.so` library is versioned, so stepping to 2.21.x probably means installing that
release's package alongside the newer one [U]. The time and locks the conversion takes on a
billion-row table are not documented [U].

### What the upgrade would change for uploads

| Change | Version | Effect on this table | Source |
| --- | --- | --- | --- |
| Leaves the removed Hypercore storage | migration | Inserts go through the standard columnstore conflict check (in-memory batch tests, above); production returns to a supported, maintained code path | `chunk_dispatch.c`, `compression_dml.c`[^tsdb-dispatch][^tsdb-dml] [V]; effect [I] |
| Vectorised constraint checks on backfill (#7972) | 2.20.0 | "up to 10x faster" upserts; the blog's test is 3,000 rows, all conflicting, 17 s → 1.7 s | CHANGELOG; 2.20 blog[^tsdb-changelog][^blog-220] [V]; no memory claim |
| Cached scan keys for repeated upserts into one compressed chunk (#8182) | 2.21.0 | 1.7 s → 0.7 s on the same test | CHANGELOG; 2.21 blog[^tsdb-changelog][^blog-221] [V]; no memory claim |
| "Fix memory leak in row compressor flush" (#8074) | 2.20.0 | the row compressor serves the compression job that runs after an upload | CHANGELOG[^tsdb-changelog] [V]; relevance [I] |
| `move_to_columnstore()` (#10632) and `timescaledb.move_to_columnstore_tuple_sort_limit`, which "limits how many tuples `move_to_columnstore()` sorts at once to bound memory usage" (default 0, no limit) | 2.31.0 | none for the 7-day policy, which still calls `compress_chunk`; the limit applies only to the internal `_timescaledb_functions.move_to_columnstore()`, so only to a custom job built on it | CHANGELOG 2.31.0[^tsdb-changelog]; `sql/policy_internal.sql` line 211, `sql/maintenance_utils.sql` line 67 and `tsl/src/compression/compression.c` line 3781 at 2.31.0[^tsdb-policy] [V]; custom-job reach [I] |
| Bloom filters prune upsert decompression (#9374) | 2.26.0/2.27.0 | probably none: the defaults build no bloom filter for a key of a `segmentby` column plus a timestamp `orderby` column | CHANGELOG; `tsl/src/compression/create.c` at 2.31.0, `create_default_composite_bloom` and `should_create_bloom_sparse_index` (line 420)[^tsdb-create] [V for the code]; effect [I] |
| "Direct compress" for inserts, with its own memory fixes (#10119) | 2.21–2.29 | none: disabled for tables with a primary key or unique index | `src/copy.c` at 2.31.0 lines 843–846[^tsdb-copy] [V] |
| In-memory recompression, compaction policies | 2.24–2.31 | possibly a cheaper backfill procedure (below) | CHANGELOG[^tsdb-changelog] [V]; usefulness [I] |

**Answer:** the upgrade is worth doing [I]. Staying on 2.19 leaves production on a storage method
TimescaleDB has removed, and later releases make conflict checks on old data faster [V]. The
evidence does not support saying it will stop the memory crashes [I].

## Question 2: what pandas 2/3 and pyarrow can add

| Option | Memory on the web server | Effect on the database | Cost to adopt | Source |
| --- | --- | --- | --- | --- |
| Keep `csv.reader` | ~30 MiB per batch | none | none | `batch_memory.py` [V] |
| `pandas.read_csv(engine="pyarrow")` | **higher**: reads the whole file into one Arrow table, then a DataFrame; `chunksize` and `iterator` are rejected | none | pandas upgrade (below) | pandas `readers.py` at 3.1.0 lines 377, 382[^pandas-readers] [V]; memory [I] |
| `pandas.read_csv(chunksize=…)` (C engine) | bounded by chunk size | none by itself | none (works in pandas 1.x) | pandas IO guide[^pandas-io] [V] |
| `pyarrow.csv.open_csv` (streaming) | bounded: one record batch per 1 MB block by default; single-threaded; types fixed from the first block unless given | none by itself | add pyarrow; pyarrow 26.0.0 needs Python ≥ 3.11, so Python 3.10 means an older pyarrow | Arrow docs and `options.h` at 26.0.0; PyPI[^arrow-csv] [V] |
| Use either to **sort, group and de-duplicate** before sending | small | **yes**: lets each statement touch one sensor and one 30-day chunk, and drop rows repeated within the file | moderate code change | [I] |
| ADBC PostgreSQL driver (`adbc_ingest`) | Arrow batches straight to COPY | none by itself; no `ON CONFLICT` mode, so the staging table stays | new driver and connection, outside the SQLAlchemy transaction | ADBC docs, `dbapi.py`[^adbc] [V] |

**What a pandas upgrade drags in:**

| Target | Python | SQLAlchemy for `read_sql`/`to_sql` | Source |
| --- | --- | --- | --- |
| pandas 2.1.x | ≥ 3.9 | ≥ 1.4.36 (the current pin allows it; raise its floor from 1.4.0) | `_optional.py` at v2.1.4[^pandas-versions] [V] |
| pandas 2.2.0 – 2.3.3 | ≥ 3.9 | ≥ 2.0.0 | whatsnew v2.2.0 line 486; `_optional.py` at v2.3.3[^pandas-versions] [V] |
| pandas 3.0 / 3.1.0 (2026-10-22) | ≥ 3.11 | ≥ 2.0.36 / ≥ 2.0.42 | `pyproject.toml` at v3.1.0; whatsnew v3.0.0[^pandas-versions] [V] |

pandas 3 does not require pyarrow; it uses it for the new default string type when it is
installed.[^pandas-versions] [V] The app calls `read_sql` with a SQLAlchemy engine or connection
at four call sites in three files: `src/odm2/base.py` lines 102 and 104,
`src/dataloaderservices/views.py` line 1162 and `src/dataloaderinterface/ajax.py` line 60
[V, grep at `e04806c`]. So pandas ≥ 2.2 means moving to SQLAlchemy 2 [I]. Python 3.11 is past
the newest Python that Django 3.2 lists on PyPI (3.10) [V for the classifiers; whether it runs
is U]. Upgrading pandas is worth doing as tech debt, but it is not needed to fix the upload
memory problem [I].

Datetime parsing changes if the parse is vectorised. pandas 2.0 infers one format from the
first value unless `format="mixed"` or `format="ISO8601"` is given, and pandas 3.0 removes
`errors="ignore"`.[^pandas-versions] [V] The current per-row `pd.to_datetime(row[0])` is not
affected [I].

## Recommendations

In order of cost [I for all]:

1. **Find the cause from the crashes already seen.** On the database server, check the kernel
   log for the OOM killer and the PostgreSQL log for "out of memory" with its memory-context
   dump. Note whether each crash came during an upload request or later, during the compression
   job.
2. **Reproduce one large upload on a staging copy** while running
   `SELECT pg_log_backend_memory_contexts(<pid>)` on the uploading session, to see which memory
   context grows. Measuring is a step beyond desk research and needs the team's approval.
3. **Run uploads one at a time, off the web request.** Queue each file and have one worker load
   it, so two uploads never overlap and a web worker timeout cannot abandon one half-way.
4. **Send each statement one sensor and one chunk.** Sort the temporary table by
   (`resultid`, `valuedatetime`), drop duplicate rows within the file, and insert one
   (`resultid`, 30-day window) per statement, so each statement's conflict checks are small.
5. **Do the #769 upgrade as a planned migration on a staging copy first:** 2.19 → 2.21.x →
   `SET ACCESS METHOD heap` → 2.31.0, with PostgreSQL 17 at 17.3 or newer. Keep
   `max_tuples_decompressed_per_dml_transaction` at its default: setting it to 0 removes the
   guard against a single statement filling the disk with decompressed rows.
6. **After the migration, load very large historical files with Timescale's backfill
   procedure.** Pause the columnstore job (`alter_job(…, scheduled => false)`),
   `convert_to_rowstore` the affected chunks, insert, `convert_to_columnstore`, and resume; with
   a large backlog, limit the job with `maxchunks_to_compress`.[^tsdb-docs-backfill] [V for the
   procedure] Three cautions. On a Hypercore chunk, `convert_to_rowstore` "fully decompresses
   the data and sets 'heap' TAM" [V, PR #8341 on 2.21[^tsdb-pr8341]]; run on production today,
   it would likely leave a mix of Hypercore and heap chunks [I]. The docs page is tagged "Old
   API since TimescaleDB v2.20.0" and its repository is archived [V]. And a 30-day chunk holds
   every sensor's data, so converting it is large; a user reported that converting a
   columnstore chunk to rowstore "could bloat the disk size and memory" [V that the user said
   so, issue #8775[^tsdb-issue-8775]; the size here is I]. This is an operator task, not a web
   request.
7. **Parse with `pyarrow.csv.open_csv`, or pandas `chunksize`,** to make steps 3, 4 and 6 cheap.
   Leave the pandas 2/3 upgrade to a separate SQLAlchemy 2 and Django round.

## Limitations and uncertainties

| Factor | Direction of error | Magnitude |
| --- | --- | --- |
| No access to crash logs, server size or `postgresql.conf` | the cause may be one this document does not consider (e.g. many connections × `work_mem`) | could change the recommendation order |
| Hypercore memory not traced to the allocation | the TAM path may hold or free more than inferred | unknown |
| Upgrade benefits measured by Timescale on 3,000 rows | real backfills of 100,000-row batches may gain more or less | unknown |
| Bloom-filter and old-chunk behaviour read from source, not run | the upgrade might help upserts more than stated | small to moderate |
| Cost of `convert_to_rowstore` on a 30-day chunk not documented | Recommendation 6 may be too costly for routine use | unknown; measure on staging |
| `batch_memory.py` uses a synthetic 8-sensor file on Python 3.13 | Python 3.10 objects are likely larger, since 3.11 stopped building a full `__dict__` for each instance [I] | not measured; still tens of MiB per batch [I] |

## Open questions

| Question | What would settle it | Who |
| --- | --- | --- |
| What process and memory context fail during a crash? | Kernel and PostgreSQL logs on the database server for past crashes; `pg_log_backend_memory_contexts` during a staging upload | MMW developers |
| Do crashes occur during the upload or during the later compression job? | Crash timestamps against upload times and the policy job's schedule (`timescaledb_information.job_stats`) | MMW developers |
| Current database server size and memory settings [U] | `SHOW shared_buffers, work_mem, maintenance_work_mem, max_connections;` and the EC2 instance type | MMW developers |
| Exact PostgreSQL 17 minor on production [U] | `SELECT version();` (≥ 17.2 for 2.21.x, ≥ 17.3 for 2.31.0) | MMW developers |
| Must the 2.21.x package be installed to step through it? [U] | Timescale's package repository for the server's OS; a dry run on staging | MMW developers |
| How long does `SET ACCESS METHOD heap` take, and what does it lock, on this table? [U] | Run it on a staging copy at 2.21.x | MMW developers |
| Is convert/insert/convert still Timescale's recommended backfill on 2.31, and what does it cost on one 30-day chunk? | docs.tigerdata.com for 2.31; a timed run on staging | MMW developers |
| Does pyarrow, or Django 3.2, run on Python 3.11 in this stack? [U] | A test environment build | MMW developers |
| Is a queue (e.g. a management command or task runner) acceptable on the web server? | Team decision | Anthony Aufdenkampe, Paul Tomasula |

## Appendix: revision history

| Revision | Date | Changes |
| --- | --- | --- |
| 1 | 2026-10-25 | First version. |

## References

[^mmw-issues]: WikiWatershed. monitor-my-watershed issues
    [#740](https://github.com/WikiWatershed/monitor-my-watershed/issues/740) (TimescaleDB and
    PostgreSQL upgrade, comments to 2025-05-01),
    [#744](https://github.com/WikiWatershed/monitor-my-watershed/issues/744) (Hypercore
    configuration SQL, comment by ptomasula, 2025-05-01) and
    [#769](https://github.com/WikiWatershed/monitor-my-watershed/issues/769). Read with
    `gh issue view`. Accessed 2026-10-25.
[^upload-code]: WikiWatershed. `src/dataloaderservices/views.py` and `environment.yml`, commit
    `82baf4d`. https://github.com/WikiWatershed/monitor-my-watershed/blob/82baf4d/src/dataloaderservices/views.py
    Accessed 2026-10-25.
[^config-wiki]: LimnoTech. ODM2DataSharingPortalConfig wiki, "Server Architecture" (private;
    last edited 2022). Accessed 2026-10-25.
[^pg17-resource]: PostgreSQL Global Development Group. *PostgreSQL 17 documentation, 19.4
    Resource Consumption* (`work_mem`, `maintenance_work_mem`, `temp_buffers`,
    `shared_buffers`). https://www.postgresql.org/docs/17/runtime-config-resource.html ; read as
    `doc/src/sgml/config.sgml` on `REL_17_STABLE`. Accessed 2026-10-25.
[^tsdb-changelog]: Timescale. *TimescaleDB CHANGELOG*, `main` (top entry 2.31.0, 2026-10-20).
    https://github.com/timescale/timescaledb/blob/main/CHANGELOG.md Accessed 2026-10-25.
[^tsdb-guc]: Timescale. TimescaleDB 2.19.3 source: `src/guc.c`
    (`max_tuples_decompressed_per_dml_transaction`, `hypercore_arrow_cache_max_entries`,
    `enable_dml_decompression_tuple_filtering` at lines 591–596),
    `tsl/src/hypercore/arrow_cache.c`, `tsl/src/hypercore/arrow_tts.c`,
    `tsl/src/compression/compression.c` (line 578), `tsl/src/compression/recompress.c`
    (lines 285, 300). https://github.com/timescale/timescaledb/tree/2.19.3 Accessed 2026-10-25.
[^tsdb-dml]: Timescale. TimescaleDB 2.19.3, `tsl/src/compression/compression_dml.c`,
    `decompress_batches_scan` (lines 504–548) and `batch_matches` (lines 590–621); and
    `tsl/src/compression/compression_scankey.c` (lines 56–90),
    https://github.com/timescale/timescaledb/blob/2.19.3/tsl/src/compression/compression_scankey.c
    https://github.com/timescale/timescaledb/blob/2.19.3/tsl/src/compression/compression_dml.c
    Accessed 2026-10-25.
[^tsdb-dispatch]: Timescale. TimescaleDB 2.19.3, `src/nodes/chunk_dispatch/chunk_dispatch.c`,
    line 442. https://github.com/timescale/timescaledb/blob/2.19.3/src/nodes/chunk_dispatch/chunk_dispatch.c#L442
    Accessed 2026-10-25.
[^tsdb-issues]: Timescale. timescaledb issues
    [#4903](https://github.com/timescale/timescaledb/issues/4903) and PR
    [#4931](https://github.com/timescale/timescaledb/pull/4931);
    [#7270](https://github.com/timescale/timescaledb/pull/7270); issue search for memory and
    out-of-memory reports on compressed and Hypercore inserts (queries in the research log).
    Accessed 2026-10-25.
[^tsdb-compat]: Timescale. TimescaleDB `src/compat/compat.h` at tags 2.21.4, 2.22.0, 2.30.2 and
    2.31.0 (lines 32–35 at 2.31.0).
    https://github.com/timescale/timescaledb/blob/2.31.0/src/compat/compat.h Accessed 2026-10-25.
[^tsdb-update-script]: Timescale. TimescaleDB 2.22.0, `sql/updates/2.21.3--2.22.0.sql`, lines
    2–9. https://github.com/timescale/timescaledb/blob/2.22.0/sql/updates/2.21.3--2.22.0.sql
    Accessed 2026-10-25.
[^tsdb-pr8341]: Timescale. PR #8341, "Allow quick migration from hypercore TAM to (columnstore)
    heap", merged 2025-07-07, with review comments.
    https://github.com/timescale/timescaledb/pull/8341 Accessed 2026-10-25.
[^tsdb-policy]: Timescale. TimescaleDB 2.31.0, `sql/policy_internal.sql` (line 211,
    `compress_chunk`), `sql/maintenance_utils.sql` (line 67, `move_to_columnstore`) and
    `tsl/src/compression/compression.c` (line 3781, the only read of
    `move_to_columnstore_tuple_sort_limit`). https://github.com/timescale/timescaledb/tree/2.31.0
    Accessed 2026-10-25.
[^tsdb-issue-8775]: Timescale. timescaledb issue #8775, "Can't automatically re-compress data
    inserted into a columnstore chunk" (opened 2025-10-14, closed).
    https://github.com/timescale/timescaledb/issues/8775 Accessed 2026-10-25.
[^tsdb-create]: Timescale. TimescaleDB 2.31.0, `tsl/src/compression/create.c`
    (`create_default_composite_bloom`; `should_create_bloom_sparse_index`, line 420).
    https://github.com/timescale/timescaledb/blob/2.31.0/tsl/src/compression/create.c
    Accessed 2026-10-25.
[^tsdb-copy]: Timescale. TimescaleDB 2.31.0, `src/copy.c`, lines 843–846.
    https://github.com/timescale/timescaledb/blob/2.31.0/src/copy.c Accessed 2026-10-25.
[^tsdb-docs-upgrade]: Timescale. Docs source, `latest` branch: `self-hosted/upgrades/minor-upgrade.md`,
    `_partials/_migrate_self_postgres_implement_migration_path.md`, `_partials/_plan_upgrade.md`.
    https://github.com/timescale/docs (archived; live site https://docs.tigerdata.com).
    Accessed 2026-10-25.
[^tsdb-docs-backfill]: Timescale. Docs source at commit `a28536b`:
    `use-timescale/hypercore/modify-data-in-hypercore.md` ("Modify large amounts of data";
    tagged "Old API since TimescaleDB v2.20.0"), `_partials/_hypercore_manual_workflow.md`,
    `_troubleshooting/columnstore-backlog-ooms.md`, `_troubleshooting/compression-dml-tuple-limit.md`.
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
[^pandas-io]: pandas. *IO tools user guide*, "Specifying the parser engine" and "Iterating
    through files chunk by chunk", v3.1.0. https://pandas.pydata.org/docs/user_guide/io.html
    Accessed 2026-10-25.
[^pandas-versions]: pandas. `pyproject.toml` at v3.1.0; `pandas/compat/_optional.py` at v2.1.4
    and v2.3.3; whatsnew v2.0.0, v2.2.0 and v3.0.0 (`doc/source/whatsnew/`); PyPI JSON for
    release dates. https://github.com/pandas-dev/pandas Accessed 2026-10-25.
[^arrow-csv]: Apache Arrow. *Reading and writing CSV files* (`docs/source/python/csv.rst`) and
    `cpp/src/arrow/csv/options.h` at apache-arrow-26.0.0; PyPI JSON for pyarrow 26.0.0.
    https://arrow.apache.org/docs/python/csv.html Accessed 2026-10-25.
[^adbc]: Apache Arrow ADBC. *PostgreSQL driver* docs (`docs/source/driver/postgresql.rst`,
    `main`) and `adbc_driver_manager/dbapi.py` at apache-arrow-adbc-24.
    https://arrow.apache.org/adbc/current/driver/postgresql.html Accessed 2026-10-25.
