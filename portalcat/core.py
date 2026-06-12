"""Core engine for portalcat — software catalog & scaffolder.

portalcat reads ``catalog-info.yaml`` *entities* (components, APIs, systems,
resources, groups, users) scattered across a repo, builds a single catalog with
an ownership + dependency graph, validates references, and can scaffold a new
component from a template.

Entities follow a small, well-defined shape:

    kind: Component
    metadata:
      name: orders-api
      tags: [go, payments]
    spec:
      owner: team-payments
      type: service
      system: commerce
      dependsOn: [Component:inventory-api, Resource:orders-db]

portalcat answers the questions an internal developer portal exists to answer:
who owns this, what does it depend on, what depends on it, and is anything
pointing at a thing that does not exist.

This is original Cognis Digital work; it shares no code, names, or branding with
any developer-portal product.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

TOOL_NAME = "portalcat"
TOOL_VERSION = "0.1.0"

KNOWN_KINDS = ("Component", "API", "System", "Resource", "Group", "User", "Domain")


class PortalError(Exception):
    """User-facing catalog error."""


# --------------------------------------------------------------------------- #
# YAML subset (multi-doc) — entities are small mappings.
# --------------------------------------------------------------------------- #

def _coerce(text: str) -> Any:
    s = text.strip()
    if s in ("", "~", "null"):
        return None
    if s in ("true", "false"):
        return s == "true"
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if len(s) >= 2 and s[0] == "[" and s[-1] == "]":
        inner = s[1:-1].strip()
        return [] if not inner else [_coerce(p) for p in inner.split(",")]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _parse_single(text: str) -> Any:
    lines = text.replace("\t", "  ").splitlines()
    toks: List[Tuple[int, str]] = []
    for raw in lines:
        out, sgl, dbl = [], False, False
        for i, ch in enumerate(raw):
            if ch == "'" and not dbl:
                sgl = not sgl
            elif ch == '"' and not sgl:
                dbl = not dbl
            elif ch == "#" and not sgl and not dbl and (i == 0 or raw[i-1] in " \t"):
                break
            out.append(ch)
        line = "".join(out).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        toks.append((indent, line.strip()))
    if not toks:
        return {}
    pos = [0]

    def kv(s):
        i = s.find(":")
        if i == -1:
            return s, ""
        k, v = s[:i].strip(), s[i+1:].strip()
        if len(k) >= 2 and k[0] == k[-1] and k[0] in "\"'":
            k = k[1:-1]
        return k, v

    def parse_block(indent):
        if pos[0] >= len(toks):
            return None
        _c, content = toks[pos[0]]
        return parse_list(indent) if content.startswith("- ") else parse_map(indent)

    def parse_list(indent):
        items = []
        while pos[0] < len(toks):
            cur, content = toks[pos[0]]
            if cur != indent or not content.startswith("- "):
                break
            inner = content[2:].strip()
            pos[0] += 1
            if ":" in inner and not (inner.find(":")+1 < len(inner)
                                     and inner[inner.find(":")+1] != " "):
                k, v = kv(inner)
                obj = {k: (_coerce(v) if v else _child(indent + 2))}
                obj.update(cont_map(indent + 2))
                items.append(obj)
            elif inner == "":
                items.append(_child(indent + 2))
            else:
                items.append(_coerce(inner))
        return items

    def cont_map(indent):
        obj = {}
        while pos[0] < len(toks):
            cur, content = toks[pos[0]]
            if cur != indent or content.startswith("- "):
                break
            k, v = kv(content)
            pos[0] += 1
            obj[k] = _coerce(v) if v else _child(indent + 2)
        return obj

    def parse_map(indent):
        obj = {}
        while pos[0] < len(toks):
            cur, content = toks[pos[0]]
            if cur != indent or content.startswith("- "):
                break
            k, v = kv(content)
            pos[0] += 1
            obj[k] = _coerce(v) if v else _child(indent + 1)
        return obj

    def _child(min_indent):
        if pos[0] >= len(toks):
            return None
        cur, content = toks[pos[0]]
        if cur < min_indent:
            return None
        return parse_list(cur) if content.startswith("- ") else parse_map(cur)

    result = parse_block(0)
    return result if result is not None else {}


def parse_entities(text: str) -> List[Dict[str, Any]]:
    text = text.strip()
    if not text:
        return []
    if text[:1] in "{[":
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    out = []
    for chunk in text.split("\n---"):
        chunk = chunk.strip().lstrip("-").strip()
        if chunk:
            obj = _parse_single(chunk)
            if isinstance(obj, dict) and obj:
                out.append(obj)
    return out


# --------------------------------------------------------------------------- #
# Catalog assembly
# --------------------------------------------------------------------------- #

def entity_ref(entity: Dict[str, Any]) -> str:
    kind = entity.get("kind", "Component")
    name = (entity.get("metadata", {}) or {}).get("name", "?")
    return f"{kind}:{name}"


def load_catalog(path: str) -> Dict[str, Dict[str, Any]]:
    """Walk a path for catalog-info files; return ref -> entity."""
    entities: Dict[str, Dict[str, Any]] = {}

    def ingest(text):
        for e in parse_entities(text):
            if e.get("kind") and (e.get("metadata") or {}).get("name"):
                entities[entity_ref(e)] = e

    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            ingest(fh.read())
        return entities
    if not os.path.isdir(path):
        raise PortalError(f"catalog path not found: {path}")
    for root, _dirs, files in os.walk(path):
        for fn in sorted(files):
            if fn in ("catalog-info.yaml", "catalog-info.yml") or \
               fn.endswith((".catalog.yaml", ".catalog.json")):
                with open(os.path.join(root, fn), "r", encoding="utf-8") as fh:
                    ingest(fh.read())
    return entities


def _normalize_ref(ref: str) -> str:
    """Accept 'Component:x' or bare 'x' (assume Component)."""
    return ref if ":" in ref else f"Component:{ref}"


def build_graph(entities: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build dependency + ownership edges and detect dangling references."""
    depends_on: Dict[str, List[str]] = {}
    depended_by: Dict[str, List[str]] = {}
    owners: Dict[str, str] = {}
    dangling: List[Dict[str, str]] = []

    for ref, e in entities.items():
        spec = e.get("spec", {}) or {}
        owner = spec.get("owner")
        if owner:
            owners[ref] = owner
            owner_ref = owner if ":" in owner else f"Group:{owner}"
            if owner_ref not in entities and owner not in entities:
                dangling.append({"from": ref, "to": owner, "via": "owner"})
        deps = spec.get("dependsOn", []) or []
        if isinstance(deps, str):
            deps = [deps]
        norm = [_normalize_ref(d) for d in deps]
        depends_on[ref] = norm
        for d in norm:
            depended_by.setdefault(d, []).append(ref)
            if d not in entities:
                dangling.append({"from": ref, "to": d, "via": "dependsOn"})

    return {"depends_on": depends_on, "depended_by": depended_by,
            "owners": owners, "dangling": dangling}


def summarize(entities: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    by_kind: Dict[str, int] = {}
    by_owner: Dict[str, int] = {}
    for ref, e in entities.items():
        by_kind[e.get("kind", "?")] = by_kind.get(e.get("kind", "?"), 0) + 1
        owner = (e.get("spec", {}) or {}).get("owner")
        if owner:
            by_owner[owner] = by_owner.get(owner, 0) + 1
    graph = build_graph(entities)
    return {"entity_count": len(entities), "by_kind": by_kind,
            "by_owner": by_owner, "dangling_count": len(graph["dangling"]),
            "dangling": graph["dangling"]}


def validate_catalog(entities: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    findings: List[Dict[str, str]] = []
    for ref, e in entities.items():
        md = e.get("metadata", {}) or {}
        if not md.get("name"):
            findings.append({"severity": "error", "ref": ref,
                             "message": "missing metadata.name"})
        if e.get("kind") not in KNOWN_KINDS:
            findings.append({"severity": "warning", "ref": ref,
                             "message": f"unknown kind: {e.get('kind')}"})
        spec = e.get("spec", {}) or {}
        if e.get("kind") in ("Component", "API", "Resource") and not spec.get("owner"):
            findings.append({"severity": "warning", "ref": ref,
                             "message": "no owner declared"})
    graph = build_graph(entities)
    for d in graph["dangling"]:
        findings.append({"severity": "error", "ref": d["from"],
                         "message": f"dangling {d['via']} -> {d['to']}"})
    errors = sum(1 for f in findings if f["severity"] == "error")
    return {"ok": errors == 0, "error_count": errors, "findings": findings}


def who_owns(entities: Dict[str, Dict[str, Any]], ref: str) -> Optional[str]:
    ref = _normalize_ref(ref)
    e = entities.get(ref)
    if not e:
        return None
    return (e.get("spec", {}) or {}).get("owner")


def impact_of(entities: Dict[str, Dict[str, Any]], ref: str) -> List[str]:
    """Everything that (transitively) depends on ``ref``."""
    ref = _normalize_ref(ref)
    graph = build_graph(entities)
    depended_by = graph["depended_by"]
    seen: set = set()
    stack = [ref]
    while stack:
        cur = stack.pop()
        for dependent in depended_by.get(cur, []):
            if dependent not in seen:
                seen.add(dependent)
                stack.append(dependent)
    return sorted(seen)


def dependencies_of(entities: Dict[str, Dict[str, Any]], ref: str) -> List[str]:
    """Everything ``ref`` (transitively) depends on."""
    ref = _normalize_ref(ref)
    graph = build_graph(entities)
    depends_on = graph["depends_on"]
    seen: set = set()
    stack = [ref]
    while stack:
        cur = stack.pop()
        for dep in depends_on.get(cur, []):
            if dep not in seen:
                seen.add(dep)
                stack.append(dep)
    return sorted(seen)


def find_orphans(entities: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    """Classify entities that may need attention.

    * unowned       — Component/API/Resource with no owner
    * no_dependents — nothing depends on them (leaf, possibly dead)
    * isolated      — no deps in or out (and not a Group/User)
    """
    graph = build_graph(entities)
    depended_by = graph["depended_by"]
    depends_on = graph["depends_on"]
    unowned, no_dependents, isolated = [], [], []
    for ref, e in entities.items():
        kind = e.get("kind")
        spec = e.get("spec", {}) or {}
        if kind in ("Component", "API", "Resource") and not spec.get("owner"):
            unowned.append(ref)
        if kind in ("Component", "API", "Resource", "System"):
            if not depended_by.get(ref):
                no_dependents.append(ref)
            if not depended_by.get(ref) and not depends_on.get(ref):
                isolated.append(ref)
    return {"unowned": sorted(unowned),
            "no_dependents": sorted(no_dependents),
            "isolated": sorted(isolated)}


def to_mermaid(entities: Dict[str, Dict[str, Any]]) -> str:
    """Render the dependency graph as a Mermaid ``graph LR`` diagram."""
    graph = build_graph(entities)
    lines = ["graph LR"]

    def node_id(ref: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "_", ref)

    # Declare nodes with a readable label.
    declared = set()
    for ref in entities:
        nid = node_id(ref)
        if nid not in declared:
            label = ref.replace('"', "'")
            lines.append(f'    {nid}["{label}"]')
            declared.add(nid)
    # Edges: A depends on B  =>  A --> B
    for ref, deps in graph["depends_on"].items():
        for d in deps:
            lines.append(f"    {node_id(ref)} --> {node_id(d)}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Scaffolder
# --------------------------------------------------------------------------- #

_PH = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


def scaffold(template_dir: str, dest_dir: str,
             values: Dict[str, str]) -> List[str]:
    """Copy a template tree to dest, substituting {{ name }} in paths + contents."""
    if not os.path.isdir(template_dir):
        raise PortalError(f"template dir not found: {template_dir}")

    def subst(text: str) -> str:
        return _PH.sub(lambda m: str(values.get(m.group(1), m.group(0))), text)

    written: List[str] = []
    for root, _dirs, files in os.walk(template_dir):
        rel = os.path.relpath(root, template_dir)
        for fn in files:
            src = os.path.join(root, fn)
            out_rel = subst(os.path.join(rel, fn)) if rel != "." else subst(fn)
            out_path = os.path.join(dest_dir, out_rel)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(src, "r", encoding="utf-8", errors="replace") as fh:
                content = subst(fh.read())
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(content)
            written.append(out_path)
    return written


# --------------------------------------------------------------------------- #
# AI hook (opt-in, default OFF)
# --------------------------------------------------------------------------- #

def suggest_owners(entities: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    unowned = [ref for ref, e in entities.items()
               if e.get("kind") in ("Component", "API", "Resource")
               and not (e.get("spec", {}) or {}).get("owner")]
    out = {"unowned": unowned, "suggestions": {},
           "_ai": "disabled — set COGNIS_AI_BACKEND to enable"}
    backend = _load_ai_backend()
    if backend is None or not backend.is_enabled() or not backend.health() or not unowned:
        return out
    try:
        resp = backend._chat(
            "Suggest a likely owning team for each entity ref. "
            "Format 'ref: team' one per line.", "\n".join(unowned))
        for line in (resp or "").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out["suggestions"][k.strip()] = v.strip()
        out["_ai"] = "suggested by local fleet"
    except Exception:
        pass
    return out


def _load_ai_backend():
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.abspath(os.path.join(here, "..", "..", "..", "_shared",
                                        "cognis_ai_backend.py"))
    if os.path.isfile(cand):
        try:
            spec = importlib.util.spec_from_file_location("cognis_ai_backend", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            return mod.CognisAIBackend()
        except Exception:
            return None
    return None
