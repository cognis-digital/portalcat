# portalcat

**A software catalog & scaffolder you can run anywhere.** Index your
`catalog-info.yaml` entities, build an ownership + dependency graph, validate
references, answer "who owns this / what depends on it", and scaffold new
components from templates — pure Python standard library.

Part of the **Cognis Neural Suite**.

---

## Why

Internal developer portals answer a few essential questions: who owns a service,
what it depends on, what breaks if it changes, and whether anything points at
something that no longer exists. portalcat answers all of those from a directory
of entity files — no portal server to host, no database, no dependencies.

## Commands

```bash
# Summarize a catalog (kinds, owners, dangling references).
python -m portalcat summary ./repo

# Validate entities + references.
python -m portalcat validate ./repo

# Ownership and blast-radius queries.
python -m portalcat owner  ./repo Component:orders-api
python -m portalcat impact ./repo Resource:orders-db

# Scaffold a new component from a template tree ({{ name }} placeholders).
python -m portalcat scaffold ./template ./new-service \
    --set name=billing-api --set owner=team-fin

# Run as a local MCP server (stdio JSON-RPC).
python -m portalcat mcp
```

## Entity model

```yaml
kind: Component          # Component | API | System | Resource | Group | User | Domain
metadata:
  name: orders-api
  tags: [go, payments]
spec:
  owner: team-payments
  system: commerce
  dependsOn: [Component:inventory-api, Resource:orders-db]
```

## What sets portalcat apart

- **Blast-radius in one command.** `impact` walks transitive dependents so you
  know what a change touches before you make it.
- **Reference integrity.** Dangling `owner`/`dependsOn` edges are flagged as
  errors — your catalog can't quietly rot.
- **Built-in scaffolder.** Stamp out a new, catalog-registered component from a
  template tree with `{{ placeholder }}` substitution in paths and contents.
- **MCP-native** (`summary` / `validate` / `impact`) and an opt-in local-fleet AI
  hook (default OFF) that suggests owners for unowned entities.

## Tests

```bash
python -m pytest -q     # or: python -m unittest discover -s tests
```

## Interoperability

`{}` composes with the 300+ tool Cognis suite — JSON in/out and a shared
OpenAI-compatible `/v1` backbone. See **[INTEROP.md](INTEROP.md)** for the
suite map, composition patterns, and reference stacks.

## License

Cognis Open Collaboration License (COCL) 1.0 — see [`LICENSE`](LICENSE).
© 2026 Cognis Digital LLC. Original Cognis work; no third-party code, names, or
branding.

<!-- cognis:domains:start -->
## Domains

**Primary domain:** Cyber & Security  ·  **JTF MERIDIAN division:** NULLBYTE · SPECTER

**Topics:** `cognis` `security` `infosec` `cybersecurity` `blue-team`

Part of the **Cognis Neural Suite** — 300+ source-available tools organized across 12 domains under the JTF MERIDIAN command structure. See the [suite on GitHub](https://github.com/cognis-digital) and [jtf-meridian](https://github.com/cognis-digital/jtf-meridian) for how the pieces fit together.
<!-- cognis:domains:end -->

## Usage — step by step

`portalcat` indexes `catalog-info.yaml` entities into an ownership + dependency graph you can validate, query, diagram, and scaffold from.

1. **Install** (pure stdlib, Python 3.10+):
   ```bash
   pip install "git+https://github.com/cognis-digital/portalcat.git"
   ```
2. **Summarize and validate** a catalog directory (validate exits non-zero on errors, so it doubles as a gate):
   ```bash
   portalcat summary ./repo
   portalcat validate ./repo
   ```
3. **Answer ownership / blast-radius questions** about an entity:
   ```bash
   portalcat owner  ./repo Component:orders-api
   portalcat impact ./repo Resource:orders-db   # what transitively depends on it
   portalcat deps   ./repo Component:orders-api  # what it depends on
   ```
4. **Use the output** — find orphans (`--format json`) or export the dependency graph as Mermaid:
   ```bash
   portalcat orphans ./repo --format json
   portalcat graph ./repo --out deps.mmd
   ```
5. **Scaffold a new component** from a template tree (`{{ name }}` placeholders), or run as a local MCP server:
   ```bash
   portalcat scaffold ./template ./new-service --set name=billing-api --set owner=team-fin
   portalcat mcp
   ```
