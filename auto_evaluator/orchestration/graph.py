from __future__ import annotations

from langgraph.graph import END, StateGraph

from auto_evaluator.agents.rubric_agent import rubric_agent
from auto_evaluator.agents.report_agent import report_agent
from auto_evaluator.state import EvaluationState


def build_rubric_graph():
    workflow = StateGraph(EvaluationState)
    workflow.add_node("rubric_agent", rubric_agent)
    workflow.set_entry_point("rubric_agent")
    workflow.add_edge("rubric_agent", END)
    return workflow.compile()


def build_report_graph():
    workflow = StateGraph(EvaluationState)
    workflow.add_node("report_agent", report_agent)
    workflow.set_entry_point("report_agent")
    workflow.add_edge("report_agent", END)
    return workflow.compile()
