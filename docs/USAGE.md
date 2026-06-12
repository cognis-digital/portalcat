# portalcat — Usage Guide

portalcat indexes `catalog-info.yaml` entities, builds an ownership + dependency
graph, and answers the questions a developer portal exists to answer.

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
References may be fully-qualified (`Component:inventory-api`) or bare
(`inventory-api`, assumed `Component:`).

## Commands

### summary / validate
```bash
python -m portalcat summary ./repo      # counts by kind/owner + dangling refs
python -m portalcat validate ./repo     # errors on dangling refs, warns on no owner
```

### owner / impact / deps
```bash
python -m portalcat owner  ./repo Component:orders-api   # -> team-payments
python -m portalcat impact ./repo Resource:orders-db     # who depends on it (blast radius)
python -m portalcat deps   ./repo Component:orders-api   # what it depends on (transitive)
```

### orphans — find things needing attention
```bash
python -m portalcat orphans ./repo
```
Reports three buckets:
- **unowned** — Component/API/Resource with no `owner`
- **no_dependents** — nothing depends on them (a leaf; possibly dead)
- **isolated** — no dependencies in *or* out

### graph — Mermaid export
```bash
python -m portalcat graph ./repo --out catalog.mmd
```
Emits a `graph LR` Mermaid diagram (A `dependsOn` B → `A --> B`). Paste into any
Markdown renderer or mermaid.live to visualize the service map.

### scaffold — stamp a new component
```bash
python -m portalcat scaffold ./template ./new-service \
    --set name=billing-api --set owner=team-fin --set system=commerce
```
`{{ placeholder }}` is substituted in both file *paths* and *contents*.

## MCP server

```bash
python -m portalcat mcp   # summary / validate / impact over stdio JSON-RPC
```

## CI recipe

```bash
# Fail the build if the catalog has dangling references:
python -m portalcat validate ./services || exit 1
# Surface ownership gaps as a report artifact:
python -m portalcat orphans ./services --format json > orphans.json
```
