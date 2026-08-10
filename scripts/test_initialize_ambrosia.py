import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("initialize-ambrosia.py")
SPEC = importlib.util.spec_from_file_location("initialize_ambrosia", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {MODULE_PATH}")
initialize_ambrosia = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = initialize_ambrosia
SPEC.loader.exec_module(initialize_ambrosia)


class InitializeAmbrosiaTest(unittest.TestCase):
    def test_minutes(self) -> None:
        cases = {
            "20分钟": 20,
            "1.5小时": 90,
            "1小时30分钟": 90,
            "无需准备": 0,
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(initialize_ambrosia.minutes(value), expected)

    def test_stable_id(self) -> None:
        path = "dishes/soup/罗宋汤.md"
        recipe_id = initialize_ambrosia.stable_id(path)
        self.assertEqual(recipe_id, initialize_ambrosia.stable_id(path))
        self.assertEqual(len(recipe_id), 32)

    def test_object_url_uses_manifest_origin(self) -> None:
        self.assertEqual(
            initialize_ambrosia.object_url(
                "https://asset.example/datasets/v1/manifest.json?token=secret",
                "datasets/v1/recipes.json",
            ),
            "https://asset.example/datasets/v1/recipes.json",
        )

    def test_dataset_validation(self) -> None:
        recipes = [{"path": "one"}]
        recipe_body = json.dumps(recipes).encode()
        digest = hashlib.sha256(recipe_body).hexdigest()
        manifest_body = json.dumps(
            {
                "complete": True,
                "count": 1,
                "expected_count": 1,
                "recipes": {"key": "recipes.json", "sha256": digest},
            }
        ).encode()

        manifest = initialize_ambrosia.decode_manifest(manifest_body, digest.upper())
        self.assertEqual(initialize_ambrosia.decode_recipes(recipe_body, manifest), recipes)

    def test_incomplete_manifest_is_rejected(self) -> None:
        body = json.dumps(
            {
                "complete": False,
                "count": 1,
                "expected_count": 2,
                "recipes": {"key": "recipes.json", "sha256": "0" * 64},
            }
        ).encode()
        with self.assertRaisesRegex(
            initialize_ambrosia.RecipeSeedError, "dataset incomplete: 1/2"
        ):
            initialize_ambrosia.decode_manifest(body)

    def test_recipe_is_mapped_to_parameterized_queries(self) -> None:
        class RecordingCursor:
            def __init__(self) -> None:
                self.calls = []

            def execute(self, statement, parameters) -> None:
                self.calls.append((statement, parameters))

            def executemany(self, statement, parameters) -> None:
                self.calls.append((statement, parameters))

        cursor = RecordingCursor()
        source = {
            "path": "dishes/soup/example.md",
            "category": "汤羹",
            "refined": {
                "title": "示例汤",
                "description": "用于测试",
                "difficulty": 2,
                "servings": "2人份",
                "ingredients": [{"name": "水", "amount": "500ml", "note": "温水"}],
                "steps": [{"order": 1, "action": "煮沸"}],
                "tips": ["趁热食用"],
                "tags": {
                    "cuisines": ["家常菜"],
                    "flavors": [],
                    "scenes": [],
                },
            },
        }

        initialize_ambrosia.upsert_recipe(cursor, source)

        ingredient_call = next(
            call for call in cursor.calls if "INSERT INTO t_ingredient" in call[0]
        )
        self.assertEqual(ingredient_call[1][0][2], "500ml")
        self.assertTrue(
            all("%s" in statement for statement, _parameters in cursor.calls)
        )


if __name__ == "__main__":
    unittest.main()
