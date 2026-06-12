# Demo 01 — Index a catalog and answer portal questions

`catalog/catalog-info.yaml` declares five entities: two services, a database, and
two owning teams, with `dependsOn` edges between them. `template/` is a scaffold
for new components.

## Run it

```bash
# Summarize the catalog (counts by kind/owner + dangling references).
python -m portalcat summary demos/01-basic/catalog

# Validate entities and references.
python -m portalcat validate demos/01-basic/catalog

# Who owns a thing?
python -m portalcat owner demos/01-basic/catalog Component:orders-api

# What breaks if I change the database? (transitive dependents)
python -m portalcat impact demos/01-basic/catalog Resource:orders-db

# Scaffold a new component from the template.
python -m portalcat scaffold demos/01-basic/template /tmp/billing-api \
    --set name=billing-api --set owner=team-fin --set system=commerce
```

## What you should see

`impact Resource:orders-db` reports `Component:orders-api` — the service that
depends on the database. `owner Component:orders-api` returns `team-payments`.
`summary` shows zero dangling references because every `dependsOn` and `owner`
points at an entity that exists.
