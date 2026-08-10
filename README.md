# Ambrosia

Ambrosia is the recipe and recommendation backend used by Zwei. It serves recipes, tags, favorites, viewing history, preferences, and contextual meal recommendations.

The service name and OAuth audience are `ambrosia`. The MySQL database remains named `zwei` so existing deployments do not need a data migration.

## Run locally

```bash
cp example.toml config.toml
make run
```

MySQL and an Aegis service key are required. OpenRouter and AMap credentials are needed only for recommendation features that call those providers.

## Recipe dataset

The database can be populated from the published HowToCook dataset:

```bash
python3 -m pip install -r scripts/requirements.txt
make initialize-ambrosia
```

Set `AMBROSIA_DB_URL` or provide `config.toml`. The initializer validates the manifest and payload checksum before writing anything.

## Development

```bash
make test
make lint
make build
```
