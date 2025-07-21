from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from app.tools.monday_tool import MondayTaskManager
import json
from datetime import datetime
from app.core.config import Config
from app.provider.azure_openai import AzureOpenAIClient
# from tools.monday_tool import MondayTaskManager
from typing import Dict, Any, List, Optional, Annotated
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
class AgentState(TypedDict):
    """State of the chatbot agent"""
    messages: Annotated[List[BaseMessage], add_messages]
    user_input: str
    intent_analysis: Dict[str, Any]
    monday_data: Dict[str, Any]
    response: str
    action_taken: str
    error: Optional[str]
    context: Dict[str, Any]

class MondayChatbotAgent:
    def __init__(self):
        self.monday_client = MondayTaskManager(api_token=Config.MONDAY_API_TOKEN)
        self.openai_client = AzureOpenAIClient()
        self.graph = self.build_graph()
    
    def build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        #Create the state graph for the chatbot agent
        workflow.add_node("analyze_input", self.analyze_input)
        workflow.add_node("fetch_monday_data", self.fetch_monday_data)
        workflow.add_node("generate_response", self.generate_response)
        workflow.add_node("send_notification", self.send_notification)
        workflow.add_node("handle_error", self.handle_error)

        # Define the workflow edges
        workflow.set_entry_point("analyze_input")

        #from analyze input, decide next step based on intent
        workflow.add_conditional_edges(
            "analyze_input",
            self.route_after_analysis,
            {
                "fetch_data": "fetch_monday_data",
                "generate_response": "generate_response",
                "error": "handle_error"
            }
        )

        workflow.add_edge("fetch_monday_data", "generate_response")

        workflow.add_conditional_edges(
            "generate_response",
            self.route_after_response,
            {
                "send_notification": "send_notification",
                "end": END,
            }
        )
        # From send_notification, end the workflow
        workflow.add_edge("send_notification", END)
        
        workflow.add_edge("handle_error", END)
        
        return workflow.compile(checkpointer=memory)
    def analyze_input(self, state: AgentState) -> AgentState:
        """Analyze user input to determine intent and extract entities"""
        try:
            user_input = state.get("user_input", "")
            if not user_input:
                # Extract from messages if user_input is empty
                messages = state.get("messages", [])
                if messages and isinstance(messages[-1], HumanMessage):
                    user_input = messages[-1].content
            
            # Analyze the message using OpenAI
            analysis = self.openai_client.analyze_user_message(
                user_input, 
                state.get("context", {})
            )
            
            state["intent_analysis"] = analysis
            state["user_input"] = user_input
            
            print(f"Intent analysis: {analysis}")
            
        except Exception as e:
            state["error"] = f"Error analyzing input: {str(e)}"
            print(f"Error in _analyze_input: {e}")
        
        return state
    def fetch_monday_data(self, state: AgentState) -> AgentState:
        """Fetch relevant data from Monday.com based on intent (với MondayTaskManager mới)"""
        try:
            analysis = state.get("intent_analysis", {})
            intent = analysis.get("intent", "")
            entities = analysis.get("entities", {})

            monday_data = {}

            self.monday_client.fetch_board_data()

            if intent in ["query_status", "deadline_inquiry"]:
                overdue = self.monday_client.get_overdue_tasks()
                upcoming = self.monday_client.get_upcoming_tasks()
                summary = self.monday_client.get_task_summary()

                monday_data["overdue_tasks"] = overdue
                monday_data["upcoming_tasks"] = upcoming
                monday_data["summary"] = summary

                mentioned_tasks = entities.get("tasks", [])
                if mentioned_tasks:
                    all_tasks = self.monday_client.get_all_task_details()
                    matching = []

                    for task in all_tasks:
                        for t_name in mentioned_tasks:
                            if t_name.lower() in task["task"].lower():
                                matching.append(task)
                                break
                    monday_data["matching_tasks"] = matching

            elif intent == "update_task":
                monday_data["update_capability"] = True

            else:
                state["error"] = f"Không hỗ trợ intent '{intent}' trong _fetch_monday_data."

            state["monday_data"] = monday_data

        except Exception as e:
            state["error"] = f"Lỗi khi lấy dữ liệu từ Monday: {str(e)}"
            print(f"Error in _fetch_monday_data: {e}")

        return state
    def generate_response(self, state: AgentState) -> AgentState:
        """Generate response using OpenAI based on analysis and Monday data"""
        try:
            user_input = state.get("user_input", "")
            analysis = state.get("intent_analysis", {})
            monday_data = state.get("monday_data", {})
            
            # Generate response using OpenAI
            response = self.openai_client.generate_response(
                user_input, 
                analysis, 
                monday_data
            )
            
            state["response"] = response
            
            # Add AI message to conversation
            messages = state.get("messages", [])
            messages.append(AIMessage(content=response))
            state["messages"] = messages
            
        except Exception as e:
            state["error"] = f"Error generating response: {str(e)}"
            print(f"Error in _generate_response: {e}")
        
        return state    
    def send_notification(self, state: AgentState) -> AgentState:
        """Send notification if required"""
        try:
            analysis = state.get("intent_analysis", {})
            response_type = analysis.get("response_type", "")
            
            if response_type == "actionable" and Config.ENABLE_MONDAY_UPDATES:
                # This is where you would implement sending updates to Monday.com
                # For now, we'll just log the action
                state["action_taken"] = "notification_sent"
                print("Notification would be sent to Monday.com")
            else:
                state["action_taken"] = "no_notification_needed"
            
        except Exception as e:
            state["error"] = f"Error sending notification: {str(e)}"
            print(f"Error in _send_notification: {e}")
        
        return state
    def handle_error(self, state: AgentState) -> AgentState:
        """Handle errors gracefully"""
        error = state.get("error", "Unknown error")
        
        error_response = "Xin lỗi, tôi gặp sự cố khi xử lý yêu cầu của bạn. Vui lòng thử lại sau hoặc liên hệ với quản trị viên."
        
        state["response"] = error_response
        
        messages = state.get("messages", [])
        messages.append(AIMessage(content=error_response))
        state["messages"] = messages
        
        print(f"Error handled: {error}")
        
        return state
    def route_after_analysis(self, state: AgentState) -> str:
        """Route to next node after input analysis"""
        if state.get("error"):
            return "error"
        
        analysis = state.get("intent_analysis", {})
        intent = analysis.get("intent", "")
        
        # Determine if we need to fetch Monday data
        if intent in ["query_status", "deadline_inquiry", "update_task"]:
            return "fetch_data"
        else:
            return "generate_response"
    
    def route_after_response(self, state: AgentState) -> str:
        """Route to next node after generating response"""
        if state.get("error"):
            return "end"
        
        analysis = state.get("intent_analysis", {})
        response_type = analysis.get("response_type", "")
        
        if response_type == "actionable":
            return "send_notification"
        else:
            return "end"
    def process_message(self, message: str,thread_id: str, context: Dict[str, Any] = None) -> str:
        """Process a user message and return response"""
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "user_input": message,
            "intent_analysis": {},
            "monday_data": {},
            "response": "",
            "action_taken": "",
            "error": None,
            "context": context or {}
        }
        
        # Run the graph
        final_state = self.graph.invoke(initial_state, 
                                        config=config,
                                        )
                                        
        print("-----------------------",final_state)
        return final_state.get("response", "Xin lỗi, tôi không thể xử lý yêu cầu của bạn.")