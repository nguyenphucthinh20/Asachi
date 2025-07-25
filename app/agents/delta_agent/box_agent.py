import os
import io
import pandas as pd
import pandasai as pai

from langgraph.graph import StateGraph, END, START
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from typing import  List, Optional, TypedDict, Annotated
from langgraph.checkpoint.memory import MemorySaver
from app.tools.box_tool import ToolBox
from .box_generator import FriendlyResponseGenerator
memory = MemorySaver()

# Define the state for our graph
class BoxAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    question: str
    df: Optional[pd.DataFrame]
    raw_result: str
    friendly_response: str
    error: Optional[str]



class BoxAgent:
    """Box chatbot agent for data analysis and queries"""
    
    def __init__(self):
        self.analyzer = ToolBox()
        self.generator = FriendlyResponseGenerator()
        self.graph = self.build_graph()

    def build_graph(self) -> StateGraph:
        """Build the agent's state graph"""
        workflow = StateGraph(BoxAgentState)

        # Add nodes
        workflow.add_node("analyze_input", self._analyze_input)
        workflow.add_node("load_data", self._load_data)
        workflow.add_node("query_data", self._query_data)
        workflow.add_node("generate_friendly_response", self._generate_friendly_response)
        workflow.add_node("handle_error", self._handle_error)

        # Define workflow edges
        workflow.set_entry_point("analyze_input")

        # Conditional routing after analysis
        workflow.add_conditional_edges(
            "analyze_input",
            self._route_after_analysis,
            {
                "load_data": "load_data",
                "error": "handle_error"
            }
        )

        workflow.add_edge("load_data", "query_data")
        workflow.add_edge("query_data", "generate_friendly_response")

        workflow.add_conditional_edges(
            "generate_friendly_response",
            self._route_after_response,
            {
                "end": END,
                "error": "handle_error"
            }
        )

        workflow.add_edge("handle_error", END)

        return workflow.compile(checkpointer=memory)

    def _analyze_input(self, state: BoxAgentState) -> BoxAgentState:
        """Analyze user input to extract question"""
        try:
            user_input = state.get("question", "")
            if not user_input:
                # Extract from messages if question is empty
                messages = state.get("messages", [])
                if messages and isinstance(messages[-1], HumanMessage):
                    user_input = messages[-1].content

            state["question"] = user_input
            print(f"---ANALYZING INPUT: {user_input}---")

        except Exception as e:
            state["error"] = f"Error analyzing input: {str(e)}"

        return state

    def _load_data(self, state: BoxAgentState) -> BoxAgentState:
        """Load data from Box Excel file"""
        try:
            print("---LOADING DATA---")
            df = self.analyzer.analyze_excel("metadata_ver2.xlsx")
            state["df"] = df

        except Exception as e:
            state["error"] = f"Error loading data: {str(e)}"

        return state

    def _query_data(self, state: BoxAgentState) -> BoxAgentState:
        """Query the loaded data"""
        try:
            print("---QUERYING DATA---")
            df = state.get("df")
            question = state.get("question", "")
            
            if df is not None and not df.empty:
                raw_result = self.analyzer.query_dataframe(df, question)
                state["raw_result"] = raw_result
            else:
                state["error"] = "No data available to query"

        except Exception as e:
            state["error"] = f"Error querying data: {str(e)}"

        return state

    def _generate_friendly_response(self, state: BoxAgentState) -> BoxAgentState:
        """Generate friendly response using the response generator"""
        try:
            print("---GENERATING FRIENDLY RESPONSE---")
            raw_result = state.get("raw_result", "")
            
            friendly_response = self.generator.generate_friendly_response(raw_result)
            state["friendly_response"] = friendly_response

            # Add AI message to conversation
            messages = state.get("messages", [])
            messages.append(AIMessage(content=friendly_response))
            state["messages"] = messages

        except Exception as e:
            state["error"] = f"Error generating friendly response: {str(e)}"

        return state

    def _handle_error(self, state: BoxAgentState) -> BoxAgentState:
        """Handle errors gracefully"""
        error = state.get("error", "Unknown error")
        
        error_response = f"Tôi xin lỗi, nhưng tôi gặp sự cố khi xử lý yêu cầu của bạn: {error}. Vui lòng thử lại sau."
        
        state["friendly_response"] = error_response
        
        messages = state.get("messages", [])
        messages.append(AIMessage(content=error_response))
        state["messages"] = messages
        
        print(f"Error handled: {error}")
        
        return state

    def _route_after_analysis(self, state: BoxAgentState) -> str:
        """Route to next node after input analysis"""
        if state.get("error"):
            return "error"
        return "load_data"

    def _route_after_response(self, state: BoxAgentState) -> str:
        """Route to next node after generating response"""
        if state.get("error"):
            return "error"
        return "end"

    def process_message(self, question: str, thread_id: str) -> str:
        """Process a user message and return response"""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            initial_state = {
                "messages": [HumanMessage(content=question)],
                "question": question,
                "df": None,
                "raw_result": "",
                "friendly_response": "",
                "error": None
            }
            
            # Run the graph
            final_state = self.graph.invoke(initial_state, config=config)
            
            response = final_state.get("friendly_response", "Tôi xin lỗi, nhưng tôi không thể xử lý yêu cầu của bạn.")
            
            print(f"Message processed successfully for thread: {thread_id}")
            return response
            
        except Exception as e:
            print(f"Failed to process message: {str(e)}")
            return "Tôi xin lỗi, nhưng tôi gặp lỗi khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."



