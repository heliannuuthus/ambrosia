<p align="center">
  <img src="./assets/brand/hero-ice.png" width="256" alt="Ambrosia logo" />
</p>

<h1 align="center">Ambrosia</h1>

Ambrosia 是 Zwei 背后的后端服务，管菜谱、标签、收藏、浏览历史、饮食偏好，以及给用户做场景化的餐食推荐。服务名和 OAuth audience 都是 `ambrosia`；为了不折腾既有部署，物理数据库的名字仍旧沿用 `zwei`。

Ambrosia is the backend behind Zwei: recipes, tags, favorites, viewing history, dietary preferences, and contextual meal recommendations. The service and OAuth audience are both `ambrosia`; the physical database keeps its historical name `zwei` for compatibility.

## 本地运行

需要 PostgreSQL，以及一个 Aegis 服务密钥。OpenRouter 和 AMap 的凭据只有用到对应推荐能力时才需要。

```bash
cp example.toml config.toml
make run
```

## 菜谱数据集

```bash
python3 -m pip install -r scripts/requirements.txt
make initialize-ambrosia
```

初始化脚本会先校验 HowToCook 清单和 payload 校验和，通过了才写入数据。

## 开发

```bash
make test
make lint
make build
```