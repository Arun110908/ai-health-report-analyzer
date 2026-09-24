"""
Multi-Agent Pipeline built with LangGraph.

Graph:  Agent1 (Report Processing) -> Agent2 (Medical Analysis)
        -> Agent3 (Recommendation) -> Agent4 (Report Generation) -> END

If the `langgraph` package is not installed in the current environment,
we transparently fall back to running the same four functions in a
plain sequential pipeline (identical behavior, zero external
dependency) so the API never breaks in a restricted environment.
"""
import logging
from app.models import PipelineState
from app.agents import (
    agent1_report_processing as a1,
    agent2_medical_analysis as a2,
    agent3_recommendation as a3,
    agent4_report_generation as a4,
)

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END

    def _build_graph():
        graph = StateGraph(PipelineState)
        graph.add_node("report_processing", a1.run)
        graph.add_node("medical_analysis", a2.run)
        graph.add_node("recommendation", a3.run)
        graph.add_node("report_generation", a4.run)

        graph.set_entry_point("report_processing")
        graph.add_edge("report_processing", "medical_analysis")
        graph.add_edge("medical_analysis", "recommendation")
        graph.add_edge("recommendation", "report_generation")
        graph.add_edge("report_generation", END)
        return graph.compile()

    _compiled_graph = _build_graph()
    _USING_LANGGRAPH = True
except Exception as e:  # noqa: BLE001
    logger.warning("LangGraph unavailable (%s); using sequential fallback pipeline.", e)
    _compiled_graph = None
    _USING_LANGGRAPH = False


def run_pipeline(state: PipelineState) -> PipelineState:
    if _USING_LANGGRAPH and _compiled_graph is not None:
        result = _compiled_graph.invoke(state)
        # langgraph returns a dict-like state; coerce back to our model
        return result if isinstance(result, PipelineState) else PipelineState(**result)

    # Sequential fallback -- identical agent order
    state = a1.run(state)
    state = a2.run(state)
    state = a3.run(state)
    state = a4.run(state)
    return state


def using_langgraph() -> bool:
    return _USING_LANGGRAPH
