"""Lightweight prompt builder extracted from agent.py.

This module is intentionally free of heavy SDK imports so the Streamlit
app can import and render prompts without importing the `agents` package
and triggering network calls at import time.
"""

from __future__ import annotations


def build_call(
    cmd: str,
    *,
    entities: list[str] | None = None,
    entity: str | None = None,
    criteria: list[str] | None = None,
    topic: str | None = None,
    urls: list[str] | None = None,
    fmt: str = "markdown",
    length_hint: str = "standard",
    tone: str = "analyst",
    assumptions_ok: bool = True,
) -> str:
    constraints = [
        f"Format: {fmt}",
        f"Length: {length_hint}",
        f"Tone: {tone}",
        f"Assumptions allowed: {'yes' if assumptions_ok else 'no'}",
    ]
    if urls:
        url_list = "\n  - " + "\n  - ".join(urls)
        constraints.append(f"URLs to research: {url_list}")
    header = "Constraints:\n- " + "\n- ".join(constraints) + "\n\n"

    # Normalize entities: prefer `entities` list, fall back to single `entity` param
    entities_list: list[str] | None = entities if entities else ([entity] if entity else None)

    if cmd == "CI_section":
        return header + f"CI_section({entity})"

    if cmd == "CI_summary":
        return header + f"CI_summary({entity})"

    if cmd == "CI_compare":
        # Allow comparing a single entity: compare against a default 'Market' baseline
        if not entities_list or len(entities_list) < 1:
            raise ValueError("CI_compare requires at least 1 entity (e.g. 'A' or 'A, B').")
        if len(entities_list) == 1:
            baseline = "Market"
            return header + f"CI_compare({entities_list[0]}, {baseline})"
        return header + f"CI_compare({entities_list[0]}, {entities_list[1]})"

    if cmd == "CI_landscape":
        # Allow a single-entity landscape: useful for focused entity analysis
        if not entities_list or len(entities_list) < 1:
            raise ValueError("CI_landscape requires at least 1 entity (e.g. 'A' or 'A, B, C').")
        return header + "CI_landscape(" + ", ".join(entities_list) + ")"

    if cmd == "CI_matrix":
        # Allow one or more entities in the matrix; criteria are required
        if not entities_list or not criteria:
            raise ValueError(
                "CI_matrix requires entities (>=1) and criteria (>=1). Provide comma-separated values."
            )
        return header + "CI_matrix(" + ", ".join(entities_list) + ", " + ", ".join(criteria) + ")"

    if cmd == "CI_signals":
        return header + f"CI_signals({topic})"

    if cmd == "CI_playbook":
        if not entity:
            raise ValueError("CI_playbook requires an entity (single name).")
        return header + f"CI_playbook({entity})"

    if cmd == "CI_price_band":
        if not entity:
            raise ValueError("CI_price_band requires an entity (single name).")
        return header + f"CI_price_band({entity})"

    raise ValueError(f"Unknown cmd: {cmd}")


__all__ = ["build_call"]
