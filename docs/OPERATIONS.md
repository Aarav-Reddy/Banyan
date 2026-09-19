# Operations and recovery

## Health and processes

`/api/health/` is a liveness response; `/api/ready/` checks the backend database. `make demo` waits for readiness and the web page before printing success. Native logs and stamped process records are under private `.runtime/`; Compose uses `docker compose logs api worker web`. Do not copy private request bodies, credentials, upload contents or database dumps into issue reports. The normal API access log is disabled; structured application logs carry operational metadata. Keep source data and `.runtime` out of Git.

Worker leases/retries are persisted in PostgreSQL. Restart a stopped worker through `make stop && make demo` (or `docker compose restart worker`). Expired leases are reclaimable; failed jobs and validation errors remain inspectable in the application. Do not manually mark a failed job complete. Database recovery and migration failures are errors rather than silent fallback to a different datastore.

## Backup and verified restore

For the native, explicitly local `philanthra_demo` database:

```sh
make backup
make restore-test
```

The backup helper creates a mode-0600 custom-format dump in `.runtime/backups`. Verification exports a repeatable-read snapshot, hashes all public-table rows from that snapshot, dumps that same snapshot, creates a fresh `philanthra_restore_verify_<pid>` database, restores it, and compares every table's count and full-row SHA-256 digest. It drops only its newly created scratch database even when comparison fails. `.runtime/restore-evidence.json` records time, table count and row count, never raw rows. PostgreSQL 17 client tools are required for PostgreSQL 17 dumps. Set `PG_BIN` on Linux if the tools are not on PATH.

Raw upload payloads currently live in private PostgreSQL `ImportBatch.raw` values and are covered by the database dump until their retention expiry. The `.runtime` volume can contain local development mail and other private operational files; any such files that must be retained need a separately protected filesystem backup. There is no public upload-serving directory. Local files are not encrypted by this application. Treat dumps as sensitive even though the default demo is fictional. Define an operator-owned encrypted backup location, access control and retention schedule before importing private data. A backup snapshot cannot retract an already downloaded export. Withdrawal immediately denies application access; physical deletion jobs and backup expiration are distinct operations. Do not restore an older backup into service until withdrawals since its creation have been reconciled.

The helper deliberately does not overwrite the working database. For recovery, stop writers, preserve the current database, restore a selected dump into a newly named database using `createdb` and `pg_restore --no-owner --exit-on-error --dbname=<new-name> <dump>`, validate contents and permissions, then explicitly configure the recovered database in a non-demo runtime. Named native demo startup refuses unrelated database names. Production restoration is an operator-controlled procedure requiring any retained private operational-file backup alignment and withdrawal reconciliation.

For Compose, use `docker compose exec -T db pg_dump -U philanthra -d philanthra_demo -Fc > <private-dump-path>` with a restrictive shell umask, and restore into a newly created scratch database inside that PostgreSQL service with matching `pg_restore`. Never expose database port 5432 publicly. Compose-specific restore execution has not been verified on the current machine because Docker is unavailable.

## Guarded demo reset

`make reset-demo CONFIRM=philanthra-demo` intentionally deletes and reseeds the named local demo database. The reset helper refuses non-demo environments, another database name, non-local hostnames, or a missing/wrong confirmation token. Stop application services and back up first; keep the database running. Reset is never part of normal startup. The launcher selects Compose when Docker is available, otherwise native mode; `PHILANTHRA_NATIVE=1` selects native explicitly. Do not use reset to repair production data.

## Reproducibility and audit boundaries

The seeded demo and default tests use stored/local fixtures with the optional model provider disabled. No live IRS/Census/model API is required. `make audit` is network dependent and reports unavailable/error rather than passing silently. Browser test databases are distinct from the working demo and backend test database. Avoid concurrently invoking two E2E fixtures because the test-only proxy owns fixed port 8081. Interrupted test processes may leave a UUID-prefixed scratch database; inspect ownership before explicit cleanup, never broadly delete matching databases.

Restore verification observed on the native environment: a full snapshot/hash comparison passed (exact latest table/row counts are in BUILD_STATUS.md). This evidence is for that run and does not certify later backups. See `docs/BUILD_STATUS.md` for the latest exact command results, restart evidence, browser evidence and remaining release blockers.

The long-running worker enqueues a deduplicated monitoring pass per watched workspace/hour and checks for the next bucket every minute. Manual Run monitoring queues an immediate pass. Only actual differences from stored revisions generate alerts. Run --once/--drain for bounded operator processing; expired leases can be reclaimed, and stale attempts cannot commit. Source/job error logs contain operational IDs/codes, not raw values.
