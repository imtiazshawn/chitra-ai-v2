from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from app.core.config import settings
from app.workflow.schemas.script import Script

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
_SYSTEM = """You are a professional short-video scriptwriter.
Given a topic, produce a structured video script in valid JSON.
Rules:
- 3 to 6 scenes only
- Each scene: 5–15 seconds
- narrator_text: clear, engaging, conversational
- visual_keywords: 2–4 specific, searchable stock-footage terms
- hook: one punchy sentence that grabs attention in 3 seconds
- call_to_action: one short closing line
Return ONLY the JSON object, no markdown, no explanation."""

_HUMAN = "Topic: {topic}"

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
])


# ---------------------------------------------------------------------------
# LLM factory — Groq primary, Gemini fallback
# ---------------------------------------------------------------------------
def _get_llm(use_fallback: bool = False):
    if not use_fallback:
        from langchain_groq import ChatGroq  # type: ignore
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.groq_api_key.get_secret_value(),
            temperature=0.7,
            max_tokens=2048,
        )
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.gemini_api_key.get_secret_value(),
        temperature=0.7,
    )


# ---------------------------------------------------------------------------
# Core generation with retry on fallback
# ---------------------------------------------------------------------------
def _generate(topic: str) -> Script:
    last_error: Exception | None = None

    for use_fallback in (False, True):
        provider = "Gemini" if use_fallback else "Groq"
        try:
            llm = _get_llm(use_fallback)
            chain = _PROMPT | llm.with_structured_output(Script)
            result = chain.invoke({"topic": topic})

            if isinstance(result, Script):
                return result

            # Some providers return dict instead of model instance
            return Script.model_validate(result)

        except ValidationError as exc:
            logger.warning("[%s] output validation failed: %s", provider, exc)
            last_error = exc
        except Exception as exc:
            logger.warning("[%s] LLM call failed: %s", provider, exc)
            last_error = exc

    raise RuntimeError(f"Script generation failed on all providers: {last_error}")


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------
def generate_script_node(state: Any) -> dict[str, Any]:
    logger.info("[%s] generate_script: topic=%r", state.job_id, state.topic)
    try:
        script = _generate(state.topic)
        logger.info(
            "[%s] generate_script: %d scenes generated",
            state.job_id, len(script.scenes),
        )
        return {"script": script}
    except Exception as exc:
        logger.error("[%s] generate_script failed: %s", state.job_id, exc)
        return {"error": f"scripting_failed: {exc}"}
