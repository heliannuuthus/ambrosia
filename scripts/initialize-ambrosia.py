#!/usr/bin/env python3
"""Download the Ambrosia recipe dataset and seed it into PostgreSQL."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST_URL = (
    "https://asset.heliannuuthus.com/datasets/howtocook/v1/manifest.json"
)
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.toml"
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")


class RecipeSeedError(RuntimeError):
    """Raised when the remote dataset or database configuration is invalid."""


@dataclass(frozen=True)
class DatasetManifest:
    count: int
    recipes_key: str
    recipes_sha256: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download, validate, and seed the Ambrosia recipe dataset."
    )
    parser.add_argument(
        "--manifest-url",
        default=os.getenv("RECIPE_SEED_MANIFEST_URL", DEFAULT_MANIFEST_URL),
        help="Dataset manifest URL.",
    )
    parser.add_argument(
        "--sha256",
        default=os.getenv("RECIPE_SEED_SHA256", ""),
        help="Optional pinned SHA-256 for the recipes payload.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("AMBROSIA_DB_URL", ""),
        help="PostgreSQL URL. Defaults to AMBROSIA_DB_URL or config.toml.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Ambrosia TOML config used when --database-url is omitted.",
    )
    return parser.parse_args()


def download(target: str) -> bytes:
    request = urllib.request.Request(
        target,
        headers={"Accept": "application/json", "User-Agent": "ambrosia-recipe-initializer"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RecipeSeedError(f"download {target}: HTTP {status}")
            body = response.read(MAX_DOWNLOAD_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise RecipeSeedError(f"download {target}: HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise RecipeSeedError(f"download {target}: {error.reason}") from error

    if len(body) > MAX_DOWNLOAD_BYTES:
        raise RecipeSeedError(f"download {target}: payload exceeds 20 MiB")
    return body


def decode_manifest(body: bytes, pinned_sha256: str = "") -> DatasetManifest:
    try:
        payload = json.loads(body)
        complete = payload["complete"]
        count = int(payload["count"])
        expected_count = int(payload["expected_count"])
        recipes_key = str(payload["recipes"]["key"])
        recipes_sha256 = str(payload["recipes"]["sha256"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RecipeSeedError(f"decode manifest: {error}") from error

    if complete is not True or count != expected_count:
        raise RecipeSeedError(f"dataset incomplete: {count}/{expected_count}")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", recipes_sha256):
        raise RecipeSeedError("manifest recipes SHA-256 is invalid")
    if pinned_sha256 and pinned_sha256.casefold() != recipes_sha256.casefold():
        raise RecipeSeedError("pinned SHA-256 mismatch")
    return DatasetManifest(count, recipes_key, recipes_sha256)


def object_url(manifest_url: str, key: str) -> str:
    parsed = urllib.parse.urlsplit(manifest_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RecipeSeedError("manifest URL must use HTTP or HTTPS")
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, "/" + key.lstrip("/"), "", "")
    )


def decode_recipes(body: bytes, manifest: DatasetManifest) -> list[dict[str, Any]]:
    digest = hashlib.sha256(body).hexdigest()
    if digest.casefold() != manifest.recipes_sha256.casefold():
        raise RecipeSeedError("recipes SHA-256 mismatch")
    try:
        recipes = json.loads(body)
    except json.JSONDecodeError as error:
        raise RecipeSeedError(f"decode recipes: {error}") from error
    if not isinstance(recipes, list):
        raise RecipeSeedError("recipes payload must be a JSON array")
    if len(recipes) != manifest.count:
        raise RecipeSeedError(f"recipe count mismatch: {len(recipes)}/{manifest.count}")
    return recipes


def load_database_url(explicit_url: str, config_path: Path) -> str:
    if explicit_url.strip():
        return explicit_url.strip()
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        database_url = str(config["db"]["url"]).strip()
    except FileNotFoundError as error:
        raise RecipeSeedError(f"Ambrosia config not found: {config_path}") from error
    except (KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise RecipeSeedError(f"read Ambrosia database config: {error}") from error
    if not database_url:
        raise RecipeSeedError("Ambrosia database URL is empty")
    return database_url


def connect_database(database_url: str) -> Any:
    try:
        import psycopg
    except ImportError as error:
        raise RecipeSeedError(
            "psycopg is required; run: pip install -r scripts/requirements.txt"
        ) from error

    parsed = urllib.parse.urlsplit(database_url)
    if parsed.scheme != "postgres" or not parsed.hostname:
        raise RecipeSeedError("database URL must use postgres://user:password@host/db")
    if not parsed.path.lstrip("/"):
        raise RecipeSeedError("database URL must include a database name")

    try:
        return psycopg.connect(database_url)
    except psycopg.Error as error:
        raise RecipeSeedError(f"connect database: {error}") from error


def stable_id(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:32]


def minutes(value: str) -> int:
    numbers = NUMBER_PATTERN.findall(value)
    if not numbers:
        return 0
    result = float(numbers[0])
    if "小时" in value:
        result *= 60
        if "分钟" in value and len(numbers) > 1:
            result += float(numbers[1])
    return int(result + 0.5)


def servings(value: str) -> int:
    match = NUMBER_PATTERN.search(value)
    if not match:
        return 1
    return max(1, int(float(match.group())))


def optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


RECIPE_UPSERT = """
INSERT INTO t_recipe (
    recipe_id, name, description, images, category, difficulty, servings,
    prep_time_minutes, cook_time_minutes, total_time_minutes
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (recipe_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    images = EXCLUDED.images,
    category = EXCLUDED.category,
    difficulty = EXCLUDED.difficulty,
    servings = EXCLUDED.servings,
    prep_time_minutes = EXCLUDED.prep_time_minutes,
    cook_time_minutes = EXCLUDED.cook_time_minutes,
    total_time_minutes = EXCLUDED.total_time_minutes
"""


def upsert_recipe(cursor: Any, source: dict[str, Any]) -> None:
    try:
        path = str(source["path"])
        category = str(source.get("category", ""))
        refined = source["refined"]
        title = str(refined["title"])
    except (KeyError, TypeError) as error:
        raise RecipeSeedError(f"invalid recipe: {error}") from error

    recipe_id = stable_id(path)
    prep_time = minutes(str(refined.get("prep_time", "")))
    cook_time = minutes(str(refined.get("cook_time", "")))
    cursor.execute(
        RECIPE_UPSERT,
        (
            recipe_id,
            title,
            optional_text(refined.get("description")),
            "[]",
            category,
            int(refined.get("difficulty", 1)),
            servings(str(refined.get("servings", ""))),
            prep_time or None,
            cook_time or None,
            (prep_time + cook_time) or None,
        ),
    )

    for table in ("t_ingredient", "t_step", "t_additional_note", "t_recipe_tag"):
        cursor.execute(f"DELETE FROM {table} WHERE recipe_id = %s", (recipe_id,))

    ingredients = refined.get("ingredients", [])
    cursor.executemany(
        """
        INSERT INTO t_ingredient (recipe_id, name, text_quantity, notes)
        VALUES (%s, %s, %s, %s)
        """,
        [
            (
                recipe_id,
                str(item["name"]),
                str(item.get("amount", "")),
                optional_text(item.get("note")),
            )
            for item in ingredients
        ],
    )
    cursor.executemany(
        """
        INSERT INTO t_step (recipe_id, step, description)
        VALUES (%s, %s, %s)
        """,
        [
            (recipe_id, int(item["order"]), str(item["action"]))
            for item in refined.get("steps", [])
        ],
    )
    cursor.executemany(
        "INSERT INTO t_additional_note (recipe_id, note) VALUES (%s, %s)",
        [(recipe_id, str(note)) for note in refined.get("tips", [])],
    )

    tags = refined.get("tags", {})
    for tag_type, values in (
        ("cuisine", tags.get("cuisines", [])),
        ("flavor", tags.get("flavors", [])),
        ("scene", tags.get("scenes", [])),
    ):
        for value in values:
            label = str(value)
            cursor.execute(
                """
                INSERT INTO t_tag (value, label, type) VALUES (%s, %s, %s)
                ON CONFLICT (type, value) DO UPDATE SET label = EXCLUDED.label, updated_at = CURRENT_TIMESTAMP
                """,
                (label, label, tag_type),
            )
            cursor.execute(
                """
                INSERT INTO t_recipe_tag (recipe_id, tag_value, tag_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (recipe_id, tag_value, tag_type) DO NOTHING
                """,
                (recipe_id, label, tag_type),
            )


def seed_database(connection: Any, recipes: list[dict[str, Any]]) -> int:
    with connection.transaction():
        with connection.cursor() as cursor:
            for source in recipes:
                try:
                    upsert_recipe(cursor, source)
                except Exception as error:
                    path = source.get("path", "<unknown>")
                    raise RecipeSeedError(f"{path}: {error}") from error
    return len(recipes)


def run(args: argparse.Namespace) -> int:
    manifest_body = download(args.manifest_url)
    manifest = decode_manifest(manifest_body, args.sha256)
    recipes_body = download(object_url(args.manifest_url, manifest.recipes_key))
    recipes = decode_recipes(recipes_body, manifest)
    database_url = load_database_url(args.database_url, args.config)
    connection = connect_database(database_url)
    try:
        return seed_database(connection, recipes)
    finally:
        connection.close()


def main() -> int:
    try:
        count = run(parse_args())
    except (RecipeSeedError, OSError) as error:
        print(f"Ambrosia 初始化失败: {error}", file=sys.stderr)
        return 1
    print(f"Ambrosia 初始化完成: {count} 道菜谱")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
