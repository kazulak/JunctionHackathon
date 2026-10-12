from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class SiteDataTests(unittest.TestCase):
    """The results page (site/) must show exactly what the archived baselines contain."""

    def test_site_data_matches_the_archived_results(self) -> None:
        spec = importlib.util.spec_from_file_location("build_site_data", REPO_ROOT / "scripts" / "build_site_data.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for name, text in module.render(module.build()).items():
            path = REPO_ROOT / "site" / "data" / name
            self.assertTrue(path.exists(), f"missing {path}; run python scripts/build_site_data.py")
            self.assertEqual(
                path.read_text(encoding="utf-8"), text, f"{name} is out of date; run python scripts/build_site_data.py"
            )


if __name__ == "__main__":
    unittest.main()
