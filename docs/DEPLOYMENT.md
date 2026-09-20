# Running Banyan

This repository provides a local pilot, not a certified production deployment. The demo contains fictional organizations, studies and credentials. Keep it bound to loopback.

## Local prerequisites

Use Node 24.14.0, Python 3.12 or 3.13, and either Docker with Compose v2 or PostgreSQL 17 binaries. `make setup` installs uv 0.12.17 and pnpm 12.4.2 under `.tools`, then installs the frozen Python and JavaScript lockfiles into the project. It does not change conda or global Python packages. Installation and browser downloads require internet; default application behavior requires no external data/model calls.

```sh
make setup
make doctor
make demo
```

Open <http://127.0.0.1:8080>. Demo users include `foundation-admin`, `ngo-owner` and `reviewer`; their shared demo-only password is `Demo-only-Banyan-2026!`. `Start Banyan Demo.command` runs the same command on macOS and supports paths containing spaces. Use `make stop` to stop app services. Re-running startup migrates and seeds idempotently; it never flushes saved work.

## Canonical Compose environment

When Docker is available, `make demo` builds API/web images and starts PostgreSQL, migration/seed init, Gunicorn, worker, web and a same-origin Nginx proxy. Only the proxy publishes a loopback port. Named database/private-runtime volumes persist through `make stop`. Never use `docker compose down --volumes` on data you need. The Compose file intentionally contains only local demo credentials; it is not a production secret configuration.

The local verification machine has no Docker. The Compose configuration has been reviewed, but image build/startup has not been executed there. This remains a distinct release verification gap; a successful native run does not prove container behavior.

The proxy is pinned to Nginx 1.30.5, the stable release listed in the [official Nginx release record](https://nginx.org/en/download.html) at implementation time. Container pull availability remains part of the unexecuted Compose check.

## Native macOS/Linux environment

Install PostgreSQL 17 with your platform package manager, then run the same commands. Homebrew's `/opt/homebrew/opt/postgresql@17/bin` is detected. For Linux or another install, set `PG_BIN` to the directory containing `initdb`, `pg_ctl`, `psql`, `createdb`, `pg_dump` and `pg_restore` (for example `/usr/lib/postgresql/17/bin`). Run as an ordinary user; PostgreSQL refuses root-owned startup.

`PHILANTHRA_NATIVE=1 make demo` selects native mode even if Docker exists. It uses project-private `.runtime/pg`, port 55432 and database `philanthra_demo`. API listens on 8000 and the web/same-origin proxy on 8080. PostgreSQL remains running when application services stop. To stop it, use the matching `pg_ctl -D "$PWD/.runtime/pg" stop -m fast`. Application PID records include process start stamps and commands so the stop helper refuses to signal a reused PID. Occupied ports belonging to untracked services are a visible error.

`make dev` starts the Next development server and the same backend/worker. Stop app services before switching between `demo` and `dev`. After source changes run `make build` followed by `make stop && make demo` to refresh a production web build; startup preserves an existing build. Local setup does not automatically load `.env` files; export needed overrides explicitly. `.env.example` documents sanitized names/defaults.

## Public read-only demo

For a deliberately public synthetic demo, run the API in `PHILANTHRA_ENV=demo` with `PHILANTHRA_DEMO_READ_ONLY=1`. Verify `/api/v1/session/` reports `demo_read_only: true` before removing any outer access gate. This blocks visitor mutations for every account, including the shared administrator/reviewer roles, while allowing login/logout, browsing and authorized exports. Password resets, invitations, uploads, edits and approvals are blocked. Session bookkeeping and access audits remain; this mode does not stop existing background jobs. Demo sign-in pages list the three shared demo credentials; they are never displayed outside demo mode.

The existing Banyan deployment uses the unchanged Sites proxy and ngrok endpoint, with private HTTPS/hostname settings in `.runtime/philanthra_tunnel_settings.py`. On that host, stop app processes, build the updated frontend, then run `python3 .runtime/start-public-demo.py` to preserve the tunnel settings and read-only mode without reseeding. That ignored helper and the private settings are host configuration, not repository assets. Do not replace this startup with plain `make demo` while the public tunnel is open: ordinary local demo mode remains editable and uses different settings. Keep the Mac, app processes and ngrok running. Public read-only demo access does not satisfy the production prerequisites below.

## Release gate and CI

`make verify` runs Ruff lint/format, Python type checks, Django system/migration drift checks, TypeScript checks, generated OpenAPI/client drift, backend tests with coverage, web component tests, production build, browser journeys, and a real-backend smoke test. `make restore-test` separately creates a coherent PostgreSQL snapshot and proves a scratch restore matches all table rows. `make audit` calls external dependency advisory services and fails on vulnerabilities or unavailable services; it is intentionally separate from offline verification.

Before browser tests install Chromium once with `bash scripts/pnpm exec playwright install chromium`. CI provisions a PostgreSQL 17 service with isolated credentials and runs the same gate, restore check and a separate network audit job. E2E and smoke runs each create a fresh UUID-named database, seed it in test mode, launch API/web/worker on dynamically allocated internal ports and expose a test-only same-origin proxy on 8081. Teardown stops child process groups and drops only that exact newly created database. The database role needs CREATEDB for tests.

CI installs matching PostgreSQL clients from the [official PostgreSQL Ubuntu package repository](https://www.postgresql.org/download/linux/ubuntu/), rather than using an older distribution client against a newer server.

## Production prerequisites

Deploy only after security/pilot review and completed container/fresh-clone verification. Supply dedicated database credentials, a strong random Django secret, exact hosts and HTTPS CSRF origins; set `PHILANTHRA_ENV=production`, debug off and no demo auth. Configure a trusted TLS reverse proxy, external encrypted database/upload/backup storage, restrictive service accounts, secret rotation, monitoring, backup retention and restore drills. `STORAGE_ENCRYPTION_ACK=configured` is an operator acknowledgment, not application-provided encryption. The bundled loopback HTTP proxy is a demo configuration and must be replaced for deployment. Configure production email explicitly before inviting users. Outbound models remain off unless authorized data-use grants and separate credentials permit them. No production launch or real private-data import has been performed.

Production WSGI and worker startup also inspect migration state and reject a copied seeded demo database (demo seed audit marker/reserved demo identities). Explicit deployment ALLOWED_HOSTS is mandatory; localhost/api/testserver defaults are rejected. A storage-encryption acknowledgment is an operator assertion, not encryption implemented by this code. Public password-reset links require PHILANTHRA_PUBLIC_ORIGIN and explicit production email enablement; local file mail remains the default development sink.
