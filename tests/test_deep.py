"""Deep tests for portalcat — graph, dangling refs, impact, scaffold, MCP."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portalcat import (
    build_graph, impact_of, load_catalog, parse_entities, scaffold,
    suggest_owners, validate_catalog, who_owns,
)
from portalcat.core import PortalError
from portalcat import mcp_server

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(REPO_ROOT, "demos", "01-basic", "catalog")
TMPL = os.path.join(REPO_ROOT, "demos", "01-basic", "template")


class TestParse(unittest.TestCase):
    def test_multidoc(self):
        ents = parse_entities("kind: Component\nmetadata:\n  name: a\n---\n"
                              "kind: API\nmetadata:\n  name: b\n")
        self.assertEqual(len(ents), 2)


class TestGraph(unittest.TestCase):
    def test_depends_and_depended(self):
        g = build_graph(load_catalog(CAT))
        self.assertIn("Resource:orders-db", g["depends_on"]["Component:orders-api"])
        self.assertIn("Component:orders-api", g["depended_by"]["Resource:orders-db"])

    def test_dangling_detected(self):
        ents = {"Component:x": {"kind": "Component", "metadata": {"name": "x"},
                                "spec": {"owner": "t", "dependsOn": ["Component:ghost"]}}}
        g = build_graph(ents)
        self.assertTrue(any(d["to"] == "Component:ghost" for d in g["dangling"]))


class TestQueries(unittest.TestCase):
    def test_who_owns(self):
        self.assertEqual(who_owns(load_catalog(CAT), "Component:orders-api"),
                         "team-payments")

    def test_who_owns_bare_ref(self):
        self.assertEqual(who_owns(load_catalog(CAT), "orders-api"), "team-payments")

    def test_impact(self):
        deps = impact_of(load_catalog(CAT), "Resource:orders-db")
        self.assertIn("Component:orders-api", deps)


class TestValidate(unittest.TestCase):
    def test_missing_owner_warns(self):
        ents = {"Component:x": {"kind": "Component", "metadata": {"name": "x"}, "spec": {}}}
        res = validate_catalog(ents)
        self.assertTrue(any("no owner" in f["message"] for f in res["findings"]))

    def test_dangling_is_error(self):
        ents = {"Component:x": {"kind": "Component", "metadata": {"name": "x"},
                                "spec": {"owner": "t", "dependsOn": ["Component:ghost"]}}}
        res = validate_catalog(ents)
        self.assertFalse(res["ok"])


class TestScaffold(unittest.TestCase):
    def test_scaffold_substitutes(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = scaffold(TMPL, tmp,
                               {"name": "billing-api", "owner": "team-fin",
                                "system": "commerce"})
            self.assertEqual(len(written), 2)
            ci = os.path.join(tmp, "catalog-info.yaml")
            with open(ci) as fh:
                text = fh.read()
            self.assertIn("name: billing-api", text)
            self.assertIn("owner: team-fin", text)

    def test_missing_template(self):
        with self.assertRaises(PortalError):
            scaffold("/no/such/tmpl", "/tmp/x", {})


class TestMcp(unittest.TestCase):
    def test_list_and_summary(self):
        tl = mcp_server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual({t["name"] for t in tl["result"]["tools"]},
                         {"summary", "validate", "impact"})
        r = mcp_server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "impact",
                       "arguments": {"path": CAT, "ref": "Resource:orders-db"}}})
        payload = json.loads(r["result"]["content"][0]["text"])
        self.assertIn("Component:orders-api", payload["dependents"])


class TestAiHook(unittest.TestCase):
    def test_off_by_default(self):
        for v in ("COGNIS_AI_BACKEND", "COGNIS_AI_ENDPOINT"):
            os.environ.pop(v, None)
        ents = {"Component:x": {"kind": "Component", "metadata": {"name": "x"}, "spec": {}}}
        out = suggest_owners(ents)
        self.assertIn("Component:x", out["unowned"])
        self.assertTrue(out["_ai"].startswith("disabled"))


if __name__ == "__main__":
    unittest.main()
