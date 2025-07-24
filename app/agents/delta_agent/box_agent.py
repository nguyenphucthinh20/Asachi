from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
import pandas as pd
import io
import os
from typing import Dict, Any, List, Optional
from app.tools.box_tool import BoxTool
# Define the AgentState as designed
class AgentState(TypedDict):
    """State of the Delta agent for ad performance analysis"""
    messages: Annotated[List[BaseMessage], add_messages]
    user_query: str
    excel_file_name: str
    excel_data: Optional[pd.DataFrame]
    processed_data: Optional[pd.DataFrame]
    ad_performance_insights: Dict[str, Any]
    recommendations: List[str]
    response: str
    error: Optional[str]
    context: Dict[str, Any]

memory = MemorySaver()

class DeltaAgent:
    def __init__(self):
        self.box_api = BoxTool()
        self.graph = self.build_graph()

    def build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        # Add nodes for the planned workflow
        workflow.add_node("analyze_user_query", self.analyze_user_query)
        workflow.add_node("fetch_ad_data", self.fetch_ad_data)
        workflow.add_node("preprocess_data", self.preprocess_data)
        workflow.add_node("perform_ad_analysis", self.perform_ad_analysis)
        workflow.add_node("generate_insights_and_recommendations", self.generate_insights_and_recommendations)
        workflow.add_node("generate_response", self.generate_response)
        workflow.add_node("handle_error", self.handle_error)

        # Define the workflow edges
        workflow.set_entry_point("analyze_user_query")

        workflow.add_conditional_edges(
            "analyze_user_query",
            self.route_after_query_analysis,
            {
                "fetch_data": "fetch_ad_data",
                "error": "handle_error"
            }
        )

        workflow.add_conditional_edges(
            "fetch_ad_data",
            self.route_after_data_fetch,
            {
                "preprocess": "preprocess_data",
                "error": "handle_error"
            }
        )

        workflow.add_edge("preprocess_data", "perform_ad_analysis")
        workflow.add_edge("perform_ad_analysis", "generate_insights_and_recommendations")
        workflow.add_edge("generate_insights_and_recommendations", "generate_response")
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile(checkpointer=memory)

