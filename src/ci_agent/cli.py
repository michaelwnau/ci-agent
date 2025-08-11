import argparse
import asyncio

from agents import Runner

from ci_agent.agent import build_call, ci_agent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmd", required=True, choices=[
        "CI_section","CI_summary","CI_compare","CI_landscape","CI_matrix",
        "CI_signals","CI_playbook","CI_price_band"
    ])
    ap.add_argument("--entities", nargs="*")
    ap.add_argument("--entity")
    ap.add_argument("--criteria", nargs="*")
    ap.add_argument("--topic")
    ap.add_argument("--format", default="markdown")
    ap.add_argument("--tone", default="analyst")
    args = ap.parse_args()

    user_input = build_call(
        args.cmd,
        entities=args.entities,
        entity=args.entity,
        criteria=args.criteria,
        topic=args.topic,
        fmt=args.format,
        tone=args.tone,
    )
    result = asyncio.run(Runner.run(ci_agent, user_input))
    print(result.final_output)

if __name__ == "__main__":
    main()
