<p align="center">
  <img src="./assets/brand/mark.svg" width="112" alt="Ambrosia logo" />
</p>

<h1 align="center">Ambrosia</h1>

<p align="center">
  <strong>Recipe catalog and contextual meal recommendations for Zwei.</strong><br />
  为 Zwei 提供菜谱目录与场景化餐食推荐。
</p>

## Overview / 项目简介

Ambrosia serves recipes, tags, favorites, viewing history, dietary preferences, and recommendation context. The service name and OAuth audience are `ambrosia`; the existing PostgreSQL database remains named `zwei` for compatibility.

Ambrosia 是 Zwei 的后端服务，负责菜谱、标签、收藏、浏览历史、饮食偏好和推荐上下文。为兼容既有部署，物理数据库名称继续使用 `zwei`。

## Run locally

```bash
cp example.toml config.toml
make run
```

PostgreSQL and an Aegis service key are required. OpenRouter and AMap credentials are needed only for recommendation features that call those providers.

## Recipe dataset

```bash
python3 -m pip install -r scripts/requirements.txt
make initialize-ambrosia
```

The initializer validates the published HowToCook manifest and payload checksum before writing data.

## Development

```bash
make test
make lint
make build
```
