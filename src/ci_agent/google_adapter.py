"""Adapter to call Google Generative (Gemini) APIs and return plain text.

This module prefers the `google.generativeai` package. It exposes a single
function `generate_from_prompt(prompt: str) -> str` that returns the generated
text or raises a RuntimeError with a clear message on failures.
"""

from __future__ import annotations

import os


def generate_from_prompt(prompt: str) -> str:
    """Generate text from a prompt using Google Generative APIs (Gemini).

    Expects `GOOGLE_API_KEY` in the environment. Optionally accepts
    `GOOGLE_MODEL` to pick a model (defaults to `gemini-1.0`).
    """
    try:
        import google.generativeai as genai
    except Exception as e:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "google.generativeai is not installed. Install with: pip install google-generativeai"
        ) from e

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not found in environment")

    # Configure client
    try:
        genai.configure(api_key=api_key)
    except Exception:
        # Some versions may use configure differently; try setting env var
        os.environ.setdefault("GOOGLE_API_KEY", api_key)

    # Prefer an explicit model from the environment; fall back to discovering
    # a supported model via the API. Older code used `gemini-1.0` which is
    # no longer available on newer API versions — prefer a modern Gemini
    # model (e.g., gemini-1.5 variants) discovered via `list_models()` when
    # possible.
    model_env = os.getenv("GOOGLE_MODEL")
    model = model_env
    if not model:
        try:
            available = genai.list_models()
            candidates = []
            for m in available:
                name = getattr(m, "name", None) or getattr(m, "model", None) or str(m)
                methods = getattr(m, "supported_generation_methods", None) or getattr(m, "supported_methods", None) or []
                # Normalize method names to strings
                method_names = []
                for mm in methods:
                    if isinstance(mm, str):
                        method_names.append(mm)
                    else:
                        # some model descriptors use objects/attrs
                        method_names.append(getattr(mm, "name", str(mm)))

                # Prefer models that support generateContent (the ADK/generative API)
                if any(x for x in ("generateContent", "generate_content", "generateContentV1") if x in method_names) or ("generateContent" in method_names) or ("chat" in method_names) or ("generate" in method_names):
                    candidates.append((name, method_names))

            # Prefer Gemini models and newer minor versions when possible
            if candidates:
                def score(nm):
                    s = 0
                    if "gemini" in nm:
                        s += 10
                    if "1.5" in nm:
                        s += 5
                    if "flash" in nm:
                        s += 2
                    return s

                candidates.sort(key=lambda x: score(x[0]), reverse=True)
                model = candidates[0][0]
            else:
                # fallback: pick the first model name if available
                if available:
                    first = getattr(available[0], "name", None) or getattr(available[0], "model", None)
                    model = first
        except Exception:
            # If listing models fails (no permission / network), fall back to
            # a reasonable modern default. The ADK docs recommend using the
            # gemini-1.5 family; the GenerativeModel helper adds the
            # 'models/' prefix when needed.
            model = os.getenv("GOOGLE_MODEL", "gemini-1.5")

    # If the model is still None, pick a pragmatic default
    if not model:
        model = "gemini-1.5"
    # Prefer using the `GenerativeModel` helper when available. It provides
    # a consistent `generate_content` API that supports multimodal and chat
    # styles. Fall back to other helper functions if the installed client is
    # an older/newer variant.
    try:
        if hasattr(genai, "GenerativeModel"):
            model_obj = genai.GenerativeModel(model)
            resp = model_obj.generate_content(prompt)
            # Prefer `.text` if available
            if hasattr(resp, "text") and resp.text:
                return resp.text
            # Try common candidate access
            if hasattr(resp, "candidates") and resp.candidates:
                cand = resp.candidates[0]
                # candidate may be a proto or object with `content`/`text`
                if hasattr(cand, "content") and cand.content:
                    c = cand.content
                    # content may have `parts` with `text`
                    if hasattr(c, "parts") and c.parts:
                        part = c.parts[0]
                        if hasattr(part, "text") and part.text:
                            return part.text
                    # or content may be a simple string
                    if isinstance(c, str) and c:
                        return c
            # Last resort: string conversion
            return str(resp)

        # Older/newer client shapes: try a few known top-level helpers
        if hasattr(genai, "generate_content"):
            resp = genai.generate_content(model=model, prompt=prompt)
            if hasattr(resp, "text"):
                return resp.text
            return str(resp)

        if hasattr(genai, "generate_text"):
            resp = genai.generate_text(model=model, prompt=prompt)
            if hasattr(resp, "text"):
                return resp.text
            # some versions return a simple string
            if isinstance(resp, str):
                return resp
            return str(resp)

        # If we get here we couldn't find a supported API
        raise RuntimeError(
            "No supported generation method found in google.generativeai client"
        )
    except Exception as e:
        raise RuntimeError(f"Google generation error: {e}") from e


__all__ = ["generate_from_prompt"]
