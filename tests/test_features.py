"""Feature tests for portalcat — deps, orphans, mermaid graph, CLI."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portalcat import (
    dependencies_of, find_orphans, load_catalog, to_mermaid,
)
from portalcat.cli import main

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(REPO_ROOT, "demos", "01-basic", "catalog")


class TestDependencies(unittest.TestCase):
    def test_deps_transitive(self):
        deps = dependencies_of(load_catalog(CAT), "Component:orders-api")
        self.assertIn("Component:inventory-api", deps)
        self.assertIn("Resource:orders-db", deps)

    def test_leaf_has_no_deps(self):
        self.assertEqual(dependencies_of(load_catalog(CAT), "Resource:orders-db"), [])


class TestOrphans(unittest.TestCase):
    def test_no_dependents_includes_leaf_services(self):
        res = find_orphans(load_catalog(CAT))
        # orders-api: nothing depends on it (top of the chain)
        self.assertIn("Component:orders-api", res["no_dependents"])

    def test_unowned_detection(self):
        entities = {
            "Component:x": {"kind": "Component", "metadata": {"name": "x"}, "spec": {}},
            "Component:y": {"kind": "Component", "metadata": {"name": "y"},
                            "spec": {"owner": "t", "dependsOn": ["Component:x"]}},
        }
        res = find_orphans(entities)
        self.assertIn("Component:x", res["unowned"])
        self.assertNotIn("Component:y", res["unowned"])

    def test_isolated(self):
        entities = {
            "Component:lonely": {"kind": "Component", "metadata": {"name": "lonely"},
                                 "spec": {"owner": "t"}},
        }
        res = find_orphans(entities)
        self.assertIn("Component:lonely", res["isolated"])


class TestMermaid(unittest.TestCase):
    def test_graph_header_and_edges(self):
        diagram = to_mermaid(load_catalog(CAT))
        self.assertTrue(diagram.startswith("graph LR"))
        # orders-api --> orders-db edge present (ids are sanitized)
        self.assertIn("Component_orders_api", diagram)
        self.assertIn("-->", diagram)

    def test_every_entity_declared(self):
        ents = load_catalog(CAT)
        diagram = to_mermaid(ents)
        # one node line per entity
        node_lines = [l for l in diagram.splitlines() if '["' in l]
        self.assertEqual(len(node_lines), len(ents))


class TestCliFeatures(unittest.TestCase):
    def test_deps_cli(self):
        self.assertEqual(main(["deps", CAT, "Component:orders-api"]), 0)

    def test_orphans_cli(self):
        self.assertEqual(main(["orphans", CAT]), 0)

    def test_orphans_json(self):
        self.assertEqual(main(["orphans", CAT, "--format", "json"]), 0)

    def test_graph_cli_stdout(self):
        self.assertEqual(main(["graph", CAT]), 0)

    def test_graph_cli_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "g.mmd")
            self.assertEqual(main(["graph", CAT, "--out", out]), 0)
            with open(out) as fh:
                self.assertIn("graph LR", fh.read())


if __name__ == "__main__":
    unittest.main()
