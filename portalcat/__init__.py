"""portalcat — software catalog & scaffolder. Part of the Cognis Neural Suite."""

from portalcat.core import (
    TOOL_NAME,
    TOOL_VERSION,
    PortalError,
    build_graph,
    entity_ref,
    impact_of,
    load_catalog,
    parse_entities,
    scaffold,
    suggest_owners,
    summarize,
    validate_catalog,
    who_owns,
)

__version__ = TOOL_VERSION

__all__ = [
    "TOOL_NAME", "TOOL_VERSION", "__version__", "PortalError",
    "build_graph", "entity_ref", "impact_of", "load_catalog", "parse_entities",
    "scaffold", "suggest_owners", "summarize", "validate_catalog", "who_owns",
]
