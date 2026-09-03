# Mobius

Mobius is an **external, storage-agnostic schema and data migration tool**. Migrations are plain Python files, discovered from a directory, executed exactly once, in order, under a distributed lock — against any combination of storages (MongoDB, PostgreSQL, MySQL, Kafka, …) in a single migration run.

> **⚠️ Disclaimer.** Mobius executes arbitrary code against your databases. It is provided **as is, without warranty of any kind** — the author gives no guarantees and accepts **no responsibility for data loss** or any other damage resulting from its use. The ambition is absolutely to ship bug-free software (see the test suite), but migrations are inherently destructive territory: **test every migration against a non-production copy first, and have backups you have actually restored from.**

## Why?

There are plenty of migration tools around, but almost all of them are bound to a single storage technology: Flyway and Liquibase speak SQL, mongock migrates Mongo, and so on. None of them can express a migration such as *"read these documents from MongoDB, create a Kafka topic, and backfill a PostgreSQL table"* as one atomic-ish, tracked, run-once unit.

Mobius fills that gap:

- **Migrations are code.** Each migration is a Python class with `validate()` and `execute()` — anything a Python driver can do, a migration can do.
- **Migrations are deployable text files.** The file you review is byte-for-byte the file that runs. Applied migrations are checksummed (md5) and a changed file is rejected on the next run.
- **Storage roles are pluggable.** Where the run history lives (*state*), where the distributed lock lives (*locker*), and what the migrations touch (*sources*) are three independent, configurable drivers. Both MongoDB and PostgreSQL can serve as state/locker.
- **Runs are safe by default.** A global distributed lock (with heartbeat) guarantees a single runner; each migration executes in an isolated child process; the run stops on the first failure and refuses to continue until an operator resolves it.

## How it works

```
                        ┌───────────────┐
   config.json ───────► │ DriverManager │ ◄── resolvers (ENV, PLAIN) inject
                        └──────┬────────┘     credentials at runtime
                               │
        ┌──────────────┬───────┴────────┬─────────────────┐
        ▼              ▼                ▼                 ▼
     state          locker           source "db"     source "queue"
  (run history)  (global lock)     (PostgreSQL…)      (Kafka…)
        ▲              ▲                ▲                 ▲
        │              │                └───── used by ───┘
   ┌────┴──────────────┴───┐                      │
   │    mobius migrate     │──── spawns ──► migration process
   └───────────────────────┘                 (one per file)
```

A `mobius migrate` run:

1. Resolves all driver configurations (secrets are pulled from resolvers — see below).
2. Acquires the **global lock** in the locker storage. If another runner holds it, mobius waits (or exits immediately with `--no-wait`). While held, a background heartbeat extends the lock TTL; if the heartbeat ever fails, the currently running migration is terminated and the run aborts.
3. Verifies the **state log** contains no `Failed` or `InProgress` entries from previous runs — if it does, the run refuses to start.
4. Scans the migrations directory for `*.py` files, sorted by filename.
5. For each migration: checks its md5 against the state log (already-applied migrations are skipped; a *changed* applied migration aborts the run), marks it `InProgress`, and executes it **in a separate child process**. The result (`Succeed` / `Skipped` / `Failed`) is written back to the state log.
6. Stops at the first failure; releases the lock on the way out. Exit code is `0` on success, `1` on any failure.

### The three storage roles

| Role | Purpose | Implemented by |
|---|---|---|
| `state` | The log of executed migrations (id, md5 hash, state, message, timestamps) | `MONGO`, `POSTGRES`, `MYSQL` |
| `locker` | The distributed lock that serializes runners | `MONGO`, `POSTGRES`, `MYSQL` |
| `sources` | Named connections handed to migrations | `MONGO`, `POSTGRES`, `MYSQL`, `KAFKA`, `ENV`, `PLAIN` |

State and locker may live in the same database or in two different ones — they are configured independently.

### Locking semantics

- One global lock, TTL 90 s by default (configurable via `settings.lockTtl`), renewed by a heartbeat thread roughly every `ttl/3`.
- If the heartbeat cannot renew the lock (row gone, connection lost), the runner **kills the in-flight migration process**, marks its log entry `Failed`, and exits — it never keeps running without the lock.
- PostgreSQL locker: acquisition is a single atomic `INSERT … ON CONFLICT DO UPDATE … WHERE valid_till < now` — an **expired** lock left by a crashed runner is taken over immediately.
- MySQL locker: same semantics via `INSERT … ON DUPLICATE KEY UPDATE` with per-column `IF(valid_till < now, …)` guards — expired locks are also taken over immediately.
- MongoDB locker: expired locks are removed by a TTL index, so takeover after a crash can lag up to ~60 s (Mongo's TTL monitor interval).

## Installation

```bash
pip install .        # installs the `mobius` console script
```

Requires Python ≥ 3.10. Storage drivers used at runtime come from `requirements.txt` (`pymongo`, `psycopg`, `PyMySQL`, `confluent-kafka`).

## Configuration

Mobius is configured with a single JSON file (default `config.json`, override with `-c`). Top level:

```json
{
  "settings": { …tool settings, optional… },
  "locker":  { …driver config… },
  "state":   { …driver config… },
  "sources": {
    "ENV":   { …driver config… },
    "db":    { …driver config… },
    "queue": { …driver config… }
  }
}
```

### Tool settings

The optional top-level `settings` object tunes the runner; omitted keys keep their defaults:

```json
"settings": {
  "lockTtl": 90,            // seconds the global lock stays valid without a heartbeat
  "lockRetryInterval": 1    // seconds between lock acquisition retries (fractions allowed)
}
```

`lockTtl` bounds how long a crashed runner blocks the next one (its lock expires after at most `lockTtl`; the heartbeat renews roughly every `lockTtl/3`, so don't set it below a few seconds). `lockRetryInterval` is how often a waiting runner re-attempts acquisition when the lock is held (ignored with `--no-wait`). Both must be positive.

Every driver config has the same shape:

```json
{
  "kind": "POSTGRES",              // driver type
  "resolver": "ENV",               // name of another source used to resolve secrets (or null)
  "properties": {                  // values the resolver looks up …
    "user": "PG_USER",
    "password": "PG_PASSWORD",
    "server": "PG_SERVER"
  },
  "config": {                      // … and interpolates into the config via %(name)s
    "connectionUrl": "postgresql://%(user)s:%(password)s@%(server)s/mydb"
  }
}
```

### Resolvers: keeping secrets out of the file

A config with `"resolver": "<source name>"` is *unresolved* until runtime. The named resolver source (typically the built-in `ENV` driver) looks up each entry in `properties` — for `ENV`, the values are **environment variable names** — and the results are substituted into `config` using `%(key)s` placeholders. Values interpolated into connection URLs are URL-quoted automatically.

This means `config.json` is safe to commit: it contains variable *names*, never credentials.

### Driver kinds

**`ENV`** — resolver that reads environment variables. Optional `config`: `prefix`, `sufix`, `separator` (default `_`) to namespace lookups (`PRE_<NAME>_POST`).

**`PLAIN`** — resolver that returns the property values as-is (useful for non-secret templating and tests).

**`MONGO`** — usable as state, locker, and source. `config`: `connectionUrl` (required), `uuid` (default `"standard"`), `maxPoolSize` (default `10`). As a source, migrations receive a `pymongo.MongoClient`.

**`POSTGRES`** — usable as state, locker, and source. `config`: `connectionUrl` (required), `connectTimeout` (default `10`), `autocommit` (default `false`). As a source, migrations receive a fresh `psycopg` connection per use; with `autocommit: false` a migration must call `connection.commit()` — an uncommitted migration rolls back (fail-closed). Set `autocommit: true` for statements that cannot run inside a transaction (`CREATE INDEX CONCURRENTLY`, `VACUUM`).

**`KAFKA`** — source only. `config`: `bootstrapServers`. Migrations receive a `confluent_kafka.admin.AdminClient`.

**`MYSQL`** — usable as state, locker, and source. `config`: `host` (required), `port` (default `3306`), `database`, `user`, `password`, `connectTimeout` (default `10`). As a source, migrations receive a fresh `PyMySQL` connection per use (autocommit off — call `connection.commit()`).

## Usage

```bash
mobius -c config.json [-l DEBUG|INFO|WARN|ERROR] <command>
```

### `generate` — create a new migration file

```bash
mobius -c config.json generate -d ./migrations
```

Creates `<id>.py` in the target directory, where `<id>` is a UTC timestamp (centiseconds). The id doubles as the migration's identity in the state log and the required class-name suffix.

### `migrate` — run pending migrations

```bash
mobius -c config.json migrate -d ./migrations [-i] [-n]
```

| Flag | Meaning |
|---|---|
| `-d, --directory` | Directory containing migration files (required) |
| `-i, --ignore-hash` | Warn instead of abort when an applied migration's file has changed. Use only when you know why the hash differs (e.g. reformatting) — it weakens the "what ran is what's on disk" guarantee. |
| `-n, --no-wait` | If the global lock is held, exit immediately instead of retrying every `settings.lockRetryInterval` seconds |

### `sources` — print resolved driver configurations

```bash
mobius -c config.json sources
```

Resolves and prints every configured driver — useful to verify a deployment's configuration and environment wiring.

### `difference`

Placeholder — not implemented yet.

## Writing migrations

Complete runnable examples — PostgreSQL DDL, Mongo document transforms, Kafka topics, a cross-storage backfill, and an autocommit `CREATE INDEX CONCURRENTLY` — live in [`examples/`](examples/README.md).

A generated file looks like this:

```python
from mobius import Migration


class Migration172535000000(Migration):
    def validate(self):
        pass

    def execute(self):
        pass

    def description(self) -> str:
        return ""
```

Rules and lifecycle:

- The file must define a class named `Migration<id>` where `<id>` is the filename without `.py`.
- `validate()` runs first — raise there to abort before any writes happen.
- `execute()` does the work. Raise `MigrationSkippedException("reason")` to record the migration as `Skipped` (a success — it will not run again); raise `MigrationFailedException("reason")` for a controlled failure. Any other exception is also recorded as `Failed`.
- `description()` is stored in the state log as the migration's message.
- `self.manager` gives access to sources by name, as a context manager:

```python
class Migration172535000000(Migration):
    def execute(self):
        with self.manager.get("db") as pg:            # psycopg connection
            pg.execute("ALTER TABLE people ADD COLUMN email text")
            pg.commit()

        with self.manager.get("nbeo") as mongo:       # MongoClient
            mongo.get_default_database().people.update_many({}, {"$set": {"v": 2}})

    def description(self):
        return "add email column, bump doc version"
```

Things to keep in mind:

- **Applied migrations are immutable.** Never edit a migration that has run anywhere; write a new one. The md5 check exists to enforce exactly this.
- **Prefer idempotent operations** (`IF NOT EXISTS`, upserts). There is no automatic rollback across heterogeneous storages — if a migration dies halfway, an operator has to decide whether re-running is safe.
- **Do not assume strict id-order across branches.** A migration merged late (with an older timestamp id) still runs — after migrations with newer ids that already ran.
- Each migration runs in a **fresh child process**: module-level state does not leak between migrations, and a hard crash cannot corrupt the runner.

### Recovering from a failed run

A `Failed` (or orphaned `InProgress`) entry in the state log blocks all future runs by design. To recover: inspect what the migration actually did, make the storage consistent, then either fix forward with a new migration and delete the failed log entry, or mark it resolved directly in the state storage (`logs` collection/table). There is no CLI for this yet.

## Testing

The test suite has two layers:

```bash
pip install -r requirements-dev.txt

# Unit tests — fast, no external services (in-memory fakes)
pytest tests --ignore=tests/integration

# Everything, including integration tests (requires Docker)
pytest
```

**Unit tests** (`tests/`) cover the locker (acquire/conflict/heartbeat/lock-loss), the state logger, config parsing and the resolver chain, the migration runner (success/skipped/failed/crash), the `generate` command, and end-to-end `migrate` scenarios (ordering, idempotence, fail-stop, hash checking, held-lock behavior) using in-memory repositories from `tests/fakes.py` — but real child processes.

**Integration tests** (`tests/integration/`) use [testcontainers](https://testcontainers-python.readthedocs.io/) to start real services and are skipped automatically when Docker is unavailable:

- `postgres:16-alpine` — lock acquisition, expired-lock takeover, heartbeat updates, and the full logs repository against real PostgreSQL;
- `mongo:7` — the same repository contracts against real MongoDB;
- `mysql:8.4` — the same repository contracts (including expired-lock takeover) against real MySQL;
- **Redpanda** (Kafka-compatible, no ZooKeeper/JVM — used instead of a Kafka container) — the Kafka driver;
- a full `mobius migrate` end-to-end run with PostgreSQL as state + locker + source and Redpanda as a second source: real migration files executed in child processes, verified by querying the resulting table, topic, state log, and lock table.

Containers are session-scoped; the first run pulls images and takes a few minutes, subsequent runs finish in well under a minute.

## Development

### Project layout

```
mobius/
├── app.py                  # CLI bootstrap: argparse, logging, command dispatch
├── config.py               # top-level config.json mapping
├── container.py            # dependency wiring (drivers, services, commands)
├── commands/               # CLI commands: generate, migrate, sources
├── commons/
│   ├── locker/             # Locker service (lock ctx manager, heartbeat, LockHandle)
│   ├── logger/             # state log service, Log model, states
│   ├── data.py             # md5, chunking helpers
│   ├── driver.py           # IDriver interface (connection/close)
│   └── resolver.py         # IResolver interface
├── drivers/
│   ├── manager.py          # DriverManager + config mapper registry
│   ├── environment/        # ENV resolver
│   ├── plain/              # PLAIN resolver
│   ├── mongo/              # Mongo driver + locks/logs repositories
│   ├── postgres/           # Postgres driver + locks/logs repositories
│   ├── kafka/              # Kafka AdminClient driver
│   └── mysql/              # MySQL driver + locks/logs repositories
└── migration/
    ├── models.py           # Migration base class + exceptions
    └── runner.py           # child-process migration executor
```

### Adding a source driver

1. Create `mobius/drivers/<name>/driver.py` implementing `IDriver` (`connection()` returns whatever migrations should receive; `close()` releases it).
2. Create `mobius/drivers/<name>/config.py` with three classes: a plain config holder, a `DriverResolvedConfig` subclass whose `initialize()` builds the driver, and a `DriverUnresolvedConfig` subclass whose `resolve(properties)` interpolates resolver output (`%(key)s`) and returns the resolved variant. Add an `IConfigDriverMapper` with a unique `JSON_KIND` mapping the JSON shape.
3. Register the mapper in `Container.driver_json_mapper` (`mobius/container.py`).
4. Add the client library to `requirements.txt` and, ideally, an integration test under `tests/integration/`.

To make a driver usable as **state** or **locker**, additionally implement `IStateDriver.get_logs_repository()` / `ILockerDriver.get_locks_repository()` returning implementations of `LogsRepository` / `LocksRepository`. The locker contract that matters: `insert` must be atomic, raise `UniqueViolationError` when the lock is held, and should take over a lock whose `valid_till` has passed; `update_by_transaction_id` must return whether exactly one row was renewed (the heartbeat relies on it to detect lock loss).

### Conventions

- Mapping between wire formats and models lives in dedicated `*Mapper` classes with a `Fields` inner class naming the raw keys — no stringly-typed keys inline.
- Storage access goes through repository interfaces (`commons/*/repository.py`); services (`Locker`, `Logger`) never touch a client directly, which is what keeps them testable with the fakes in `tests/fakes.py`.
- Logs are structured JSON (one object per line) — suitable for log collectors out of the box.

### Known gaps

- `difference` command is a stub.
- No CLI for resolving stuck `Failed`/`InProgress` state entries (manual state-storage edit required).
