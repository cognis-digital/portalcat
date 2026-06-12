"""Smoke tests for portalcat. Standard library only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portalcat import TOOL_NAME, TOOL_VERSION, load_catalog, summarize, validate_catalog
from portalcat.cli import main

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(REPO_ROOT, "demos", "01-basic", "catalog")


class TestMetadata(unittest.TestCase):
    def test_metadata(self):
        self.assertEqual(TOOL_NAME, "portalcat")
        self.assertTrue(TOOL_VERSION)


class TestCatalog(unittest.TestCase):
    def test_load_and_summary(self):
        ents = load_catalog(CAT)
        self.assertEqual(len(ents), 5)
        info = summarize(ents)
        self.assertEqual(info["by_kind"]["Component"], 2)
        self.assertEqual(info["dangling_count"], 0)

    def test_valid_catalog(self):
        self.assertTrue(validate_catalog(load_catalog(CAT))["ok"])


class TestCli(unittest.TestCase):
    def test_summary(self):
        self.assertEqual(main(["summary", CAT]), 0)

    def test_validate(self):
        self.assertEqual(main(["validate", CAT]), 0)

    def test_owner(self):
        self.assertEqual(main(["owner", CAT, "Component:orders-api"]), 0)

    def test_impact(self):
        self.assertEqual(main(["impact", CAT, "Resource:orders-db"]), 0)

    def test_no_command_exits_2(self):
        self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
