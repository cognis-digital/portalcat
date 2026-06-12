"""portalcat — software catalog & scaffolder. Part of the Cognis Neural Suite."""

from portalcat.core import (
    TOOL_NAME,
    TOOL_VERSION,
    PortalError,
    build_graph,
    dependencies_of,
    entity_ref,
    find_orphans,
    impact_of,
    load_catalog,
    parse_entities,
    scaffold,
    suggest_owners,
    summarize,
    to_mermaid,
    validate_catalog,
    who_owns,
)

__version__ = TOOL_VERSION

__all__ = [
    "TOOL_NAME", "TOOL_VERSION", "__version__", "PortalError",
    "build_graph", "dependencies_of", "entity_ref", "find_orphans",
    "impact_of", "load_catalog", "parse_entities", "scaffold",
    "suggest_owners", "summarize", "to_mermaid", "validate_catalog", "who_owns",
]
