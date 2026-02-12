# Tests

## Setup
1. Optional (recommended): set `DATABASE_URL_TEST` to a dedicated Postgres DB URL.
2. If `DATABASE_URL_TEST` is not set, tests will derive a URL from `DATABASE_URL` and use DB name `testapp_test_db`.

Example:

```bash
export DATABASE_URL_TEST='postgresql://user:pass@localhost:5432/testapp_test_db'
```

## Run

```bash
pytest
```
