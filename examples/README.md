# Examples

`config.json` defines a PostgreSQL state + locker and four sources (two PostgreSQL
variants, MongoDB, Kafka), with all credentials resolved from environment variables.

`migrations/` shows the common patterns, one per file:

| Migration | Pattern |
|---|---|
| `172530000001.py` | PostgreSQL DDL + seed data; `validate()` guarding the target; explicit `commit()` |
| `172530000002.py` | MongoDB document transformation; `MigrationSkippedException` when there is nothing to do |
| `172530000003.py` | Kafka topic creation, skip when it already exists |
| `172530000004.py` | Cross-storage backfill: MongoDB → PostgreSQL in batches |
| `172530000005.py` | `CREATE INDEX CONCURRENTLY` via a dedicated autocommit source |

Run them (against your own throwaway databases — see the disclaimer in the main README):

```bash
export PG_USER=… PG_PASSWORD=… PG_SERVER=… \
       MONGO_USER=… MONGO_PASSWORD=… MONGO_SERVER=… MONGO_DB=… \
       KAFKA_SERVER=…

mobius -c examples/config.json migrate -d examples/migrations
```
