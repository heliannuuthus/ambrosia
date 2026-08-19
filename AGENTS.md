# Ambrosia

This repository owns the recipe and recommendation backend consumed by Zwei.

## Naming

- The backend service, Go module, OAuth audience, and environment prefix are `ambrosia`.
- The client application remains Zwei.
- The physical PostgreSQL database remains `zwei` for data compatibility.

## Commands

```bash
make test
make lint
make build
make run
make initialize-ambrosia
```

## Verification

- Run Go tests and the Python initializer tests after schema or dataset changes.
- Keep recipe IDs stable across repeated imports.
- Keep SQL writes parameterized and validate remote dataset checksums before seeding.
