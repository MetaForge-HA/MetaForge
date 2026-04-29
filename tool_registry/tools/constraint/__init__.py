"""Constraint engine MCP tool — exposes constraint.validate (MET-383).

Wraps the existing ``twin_core.constraint_engine`` so the harness can
ask "would this proposed change violate any constraints?" via the
standard MCP surface.
"""
