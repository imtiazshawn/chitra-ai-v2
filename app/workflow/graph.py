from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.workflow.nodes.assets import fetch_assets_node
from app.workflow.nodes.audio import generate_audio_node
from app.workflow.nodes.script import generate_script_node
from app.workflow.nodes.sync import sync_captions_node
from app.workflow.state import Nodes, PipelineState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node stubs — each will be replaced with real implementation in Module 2.x
# ---------------------------------------------------------------------------

def generate_script(state: PipelineState) -> dict[str, Any]:
    return generate_script_node(state)


def generate_audio(state: PipelineState) -> dict[str, Any]:
    return generate_audio_node(state)


def sync_captions(state: PipelineState) -> dict[str, Any]:
    return sync_captions_node(state)


def fetch_assets(state: PipelineState) -> dict[str, Any]:
    return fetch_assets_node(state)


def render_video(state: PipelineState) -> dict[str, Any]:
    """Module 2.6 — runs MoviePy/FFmpeg pipeline, returns output video path."""
    logger.info("[%s] render_video: stub", state.job_id)
    return {"output_video_path": ""}


# ---------------------------------------------------------------------------
# Conditional edge — route to END on any error
# ---------------------------------------------------------------------------

def should_continue(state: PipelineState) -> str:
    if state.error:
        logger.error("[%s] pipeline aborted: %s", state.job_id, state.error)
        return END
    return "continue"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    graph = StateGraph(PipelineState)

    # Register nodes
    graph.add_node(Nodes.SCRIPT, generate_script)
    graph.add_node(Nodes.AUDIO,  generate_audio)
    graph.add_node(Nodes.SYNC,   sync_captions)
    graph.add_node(Nodes.ASSETS, fetch_assets)
    graph.add_node(Nodes.RENDER, render_video)

    # Entry point
    graph.add_edge(START, Nodes.SCRIPT)

    # Linear pipeline with error check after each node
    for src, dst in [
        (Nodes.SCRIPT, Nodes.AUDIO),
        (Nodes.AUDIO,  Nodes.SYNC),
        (Nodes.SYNC,   Nodes.ASSETS),
        (Nodes.ASSETS, Nodes.RENDER),
    ]:
        graph.add_conditional_edges(
            src,
            should_continue,
            {"continue": dst, END: END},
        )

    # Final node → END
    graph.add_edge(Nodes.RENDER, END)

    return graph


# Compiled graph — import this in tasks/workers
pipeline = build_graph().compile()
