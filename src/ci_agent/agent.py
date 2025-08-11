from __future__ import annotations

import asyncio
import json

from agents import Agent, GuardrailFunctionOutput, InputGuardrail, Runner, function_tool
from pydantic import BaseModel

CI_META_LANGUAGE = """
You are a competitive intelligence analyst. Follow the meta language below. If information is unknown,
state assumptions explicitly and proceed.

When I say "CI_section(<entity>)", I mean:
Produce a structured CI section for <entity> with: Summary (3–5 sentences), Strengths, Weaknesses, Opportunities, Threats.

When I say "CI_summary(<entity>)", I mean:
Produce a 120–180 word executive summary of <entity>'s competitive positioning.

When I say "CI_compare(<A>, <B>)", I mean:
Provide a side-by-side comparison of <A> and <B> covering market presence, technical capability, pricing posture,
notable customers, and recent momentum signals.

When I say "CI_landscape(<list>)", I mean:
Given a comma-separated list of entities, produce a market landscape that includes:
1) one-line positioning for each,
2) a capability-by-entity table with Normalized Ratings (Low/Med/High) for: Data/AI, Platform maturity, Security/Compliance,
   Services scale, Partner ecosystem,
3) a brief analyst note on differentiation and likely head-to-head matchups.

When I say "CI_matrix(<list>, <criteria>)", I mean:
Create a decision matrix scoring each entity in <list> against comma-separated <criteria>.
Use a 1–5 score with a one-line rationale per cell and a total score.

When I say "CI_signals(<topic>)", I mean:
List near-term signals to watch for <topic> over the next 6–12 months, grouped as Product, Partnerships,
Hiring, Contracts. For each signal, include why it matters and an indicative metric or proxy.

When I say "CI_playbook(<entity>)", I mean:
Provide three win themes, three land-and-expand plays, and three counter-moves against <entity> with concrete proof-points.

When I say "CI_price_band(<entity>)", I mean:
State typical pricing posture (premium/market/discount), what drives it, and common bundling or TCV patterns.
If unknown, infer with stated assumptions.

Output policy:
- Default to Markdown tables where appropriate.
- If the caller requests "json" format, return valid JSON with fields mirroring the structure.
- Always state assumptions when you infer.

Few-shot anchors:
Example A:
Input: CI_section(Acme Analytics)
Output:
Summary: Acme Analytics provides enterprise data integration and BI tooling…
Strengths: …
Weaknesses: …
Opportunities: …
Threats: …

Example B:
Input: CI_compare(Acme Analytics, Beta Platforms)
Output:
| Dimension | Acme Analytics | Beta Platforms |
| …        | …              | …              |
"""

class MatrixSpec(BaseModel):
    entities: list[str]
    criteria: list[str]

@function_tool
def validate_matrix_spec(spec: MatrixSpec) -> str:
    """Validate matrix inputs and echo them back.
    Args:
        spec: JSON with 'entities' (>=2) and 'criteria' (>=1).
    """
    if len(spec.entities) < 2:
        return json.dumps({"ok": False, "error": "Need at least two entities"})
    if len(spec.criteria) < 1:
        return json.dumps({"ok": False, "error": "Need at least one criterion"})
    return json.dumps({"ok": True, "entities": spec.entities, "criteria": spec.criteria})

class CIInputCheck(BaseModel):
    is_ci: bool
    why: str

guardrail_agent = Agent(
    name="CI Guardrail",
    instructions="Classify if the input is a competitive-intelligence request; return JSON with is_ci and why.",
    output_type=CIInputCheck,
)

async def input_guardrail(ctx, agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    final = result.final_output_as(CIInputCheck)
    return GuardrailFunctionOutput(output_info=final, tripwire_triggered=not final.is_ci)

ci_agent = Agent(
    name="CI Agent",
    instructions=CI_META_LANGUAGE,
    tools=[validate_matrix_spec],
    input_guardrails=[InputGuardrail(guardrail_function=input_guardrail)],
)

def build_call(
    cmd: str,
    *,
    entities: list[str] | None = None,
    entity: str | None = None,
    criteria: list[str] | None = None,
    topic: str | None = None,
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
    header = "Constraints:\n- " + "\n- ".join(constraints) + "\n\n"
    if cmd == "CI_section":
        return header + f"CI_section({entity})"
    if cmd == "CI_summary":
        return header + f"CI_summary({entity})"
    if cmd == "CI_compare":
        assert entities and len(entities) == 2
        return header + f"CI_compare({entities[0]}, {entities[1]})"
    if cmd == "CI_landscape":
        assert entities and len(entities) >= 2
        return header + "CI_landscape(" + ", ".join(entities) + ")"
    if cmd == "CI_matrix":
        assert entities and criteria
        return header + "CI_matrix(" + ", ".join(entities) + ", " + ", ".join(criteria) + ")"
    if cmd == "CI_signals":
        return header + f"CI_signals({topic})"
    if cmd == "CI_playbook":
        return header + f"CI_playbook({entity})"
    if cmd == "CI_price_band":
        return header + f"CI_price_band({entity})"
    raise ValueError(f"Unknown cmd: {cmd}")

async def demo():
    user_input = build_call(
        "CI_landscape",
        entities=["RAFT, Inc.", "Palantir", "Anduril"],
        fmt="markdown",
        length_hint="standard",
        tone="analyst",
    )
    result = await Runner.run(ci_agent, user_input)
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(demo())
