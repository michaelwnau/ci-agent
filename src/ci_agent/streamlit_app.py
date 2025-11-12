import asyncio
import json
import os

import streamlit as st
from dotenv import load_dotenv

# Import the lightweight prompt builder only (avoid importing the heavy
# `agents` SDK or `ci_agent.agent` at module import time because those
# imports may initialize OpenAI clients immediately and cause 401s when a
# placeholder OPENAI_API_KEY is present). We'll import the full agent
# machinery lazily inside `_run_agent_sync` only when the OpenAI path is
# actually needed.
from ci_agent.call_builder import build_call

load_dotenv()

# Read optional integration keys from the environment (loaded from local .env)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

st.set_page_config(page_title="CI Agent", layout="wide")

st.title("Competitive Intelligence Agent")
st.caption("Meta Language + OpenAI Agents SDK • Streamlit UI")  # no emoji

with st.sidebar:
    st.header("Request")
    cmd: str = st.selectbox(
        "Command",
        [
            "CI_section",
            "CI_summary",
            "CI_compare",
            "CI_landscape",
            "CI_matrix",
            "CI_signals",
            "CI_playbook",
            "CI_price_band",
        ],
        index=3,
    )

    fmt = st.selectbox("Format", ["markdown", "json", "text"], index=0)
    tone = st.selectbox("Tone", ["analyst", "neutral", "exec"], index=0)
    length_hint = st.selectbox("Length hint", ["short", "standard", "extended"], index=1)
    assumptions_ok = st.checkbox("Allow assumptions (state explicitly)", value=True)

    st.markdown("---")
    st.subheader("Inputs")

    entity: str | None = None
    entities_raw: str | None = None
    criteria_raw: str | None = None
    topic: str | None = None
    urls_raw: str | None = None

    # URL input available for all command types
    st.info(
        "Enter specific URLs for the agent to research. The analysis will be based primarily on information from these sources."
    )
    urls_raw = st.text_area(
        "Research URLs (comma-separated, max 3)",
        placeholder="e.g., https://company1.com, https://company2.com, https://company3.com",
        height=50,
    )

    if cmd in {"CI_section", "CI_summary", "CI_playbook", "CI_price_band"}:
        entity = st.text_input("Entity", placeholder="e.g., Company Name")

    if cmd in {"CI_compare", "CI_landscape", "CI_matrix"}:
        entities_raw = st.text_area(
            "Entities (comma-separated)",
            value="Company A, Company B, Company C"
            if cmd != "CI_compare"
            else "Company A, Company B",
            height=70,
        )

        # If user provided exactly one entity for CI_compare, show a helper note
        if cmd == "CI_compare" and entities_raw:
            provided = [x.strip() for x in entities_raw.split(",") if x.strip()]
            if len(provided) == 1:
                st.info(
                    f"Comparing to default baseline: Market (single entity provided: {provided[0]})"
                )

    if cmd == "CI_matrix":
        criteria_raw = st.text_input(
            "Criteria (comma-separated)",
            value="Evaluation speed, ATO readiness, Integration effort, TCO 3yr",
        )

    if cmd == "CI_signals":
        topic = st.text_input(
            "Topic", placeholder="e.g., AI-enabled knowledge management in U.S. federal market"
        )

    st.markdown("---")
    # Integrations section (detect presence of GOOGLE_API_KEY in local .env)
    st.subheader("Integrations")
    if GOOGLE_API_KEY:
        use_google = st.checkbox(
            "Enable Google API usage",
            value=False,
            help="Uses GOOGLE_API_KEY from your local .env (value is not shown).",
        )
    else:
        st.info(
            "Set `GOOGLE_API_KEY` in your local `.env` to enable Google API features (do not commit this file)."
        )
        use_google = False

    # persist preference in session state for use when running
    st.session_state["use_google"] = use_google

    run_btn = st.button("Run Agent", type="primary")
    clear_btn = st.button("Clear")

if clear_btn:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    # Use `st.rerun()` which is the supported API in current Streamlit versions
    # (older code used `st.experimental_rerun()` which may not exist).
    st.rerun()


def _split_csv(s: str | None) -> list[str] | None:
    if not s:
        return None
    return [x.strip() for x in s.split(",") if x.strip()]


def _build_user_input() -> str:
    entities = _split_csv(entities_raw) if entities_raw else None
    criteria = _split_csv(criteria_raw) if criteria_raw else None
    urls = _split_csv(urls_raw) if urls_raw else None

    # Limit to max 3 URLs
    if urls and len(urls) > 3:
        urls = urls[:3]
        st.warning("Limited to first 3 URLs.")

    # Warn if no URLs are provided
    if not urls:
        st.warning(
            "No research URLs provided. For more accurate and factual results, consider adding specific URLs to research."
        )

    return build_call(
        cmd,
        entities=entities,
        entity=entity,
        criteria=criteria,
        topic=topic,
        urls=urls,
        fmt=fmt,
        length_hint=length_hint,
        tone=tone,
        assumptions_ok=assumptions_ok,
    )


def _run_agent_sync(user_input: str) -> str:
    # Decide which backend to use. Guard access to session_state in case the
    # Streamlit runtime hasn't initialized it yet.
    try:
        use_google = bool(st.session_state.get("use_google")) and bool(GOOGLE_API_KEY)
    except Exception:
        use_google = False

    if use_google:
        # Mark which key/source we used (non-secret). This helps debugging in
        # the UI/logs without exposing any API key values.
        st.session_state["ci_agent_key_source"] = "GOOGLE"
        try:
            from ci_agent.google_adapter import generate_from_prompt

            return generate_from_prompt(user_input)
        except Exception as e:
            # Surface Google-specific errors clearly to the UI
            raise RuntimeError(f"Google adapter error: {e}") from e

    # Fallback: use the original agents/Runner path (this will import the
    # heavy `agents` SDK and the `ci_agent.agent` module). Import lazily so we
    # don't trigger OpenAI client initialization when the Google path is
    # selected.
    st.session_state["ci_agent_key_source"] = "OPENAI"
    try:
        import importlib

        agents = importlib.import_module("agents")
        agent_module = importlib.import_module("ci_agent.agent")
        Runner = agents.Runner
        return asyncio.run(Runner.run(agent_module.ci_agent, user_input)).final_output
    except Exception as e:
        raise RuntimeError(f"Agents/OpenAI path error: {e}") from e


col_prompt, col_output = st.columns(2, gap="large")

with col_prompt:
    st.subheader("Prompt (User Input to Agent)")
    if run_btn:
        try:
            user_input = _build_user_input()
            st.code(user_input, language="markdown")
            st.session_state["last_prompt"] = user_input
        except Exception as e:
            st.error(f"Build error: {e}")

with col_output:
    st.subheader("Agent Output")
    if run_btn and "last_prompt" in st.session_state:
        try:
            output = _run_agent_sync(st.session_state["last_prompt"])
            st.session_state["last_output"] = output
        except Exception as e:
            st.error(f"Agent error: {e}")

    if "last_output" in st.session_state:
        out_text = st.session_state["last_output"]
        if fmt == "json":
            try:
                parsed = json.loads(out_text)
                st.json(parsed)
            except Exception:
                st.warning("Output was not valid JSON; showing raw text.")
                st.code(out_text, language="markdown")
        else:
            if fmt == "markdown":
                st.markdown(out_text)
            else:
                st.code(out_text, language="markdown")

        st.markdown("---")
        dl_name = f"{cmd.lower()}_output.{'json' if fmt == 'json' else 'md'}"
        st.download_button(
            label=f"Download {dl_name}",
            data=out_text if isinstance(out_text, str) else json.dumps(out_text, indent=2),
            file_name=dl_name,
            mime="application/json" if fmt == "json" else "text/markdown",
        )
