from enum import Enum
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from typing import Dict, Any, List, Optional
from app.agents.base_agent import ChatbotAgent
from app.agents.alpha_agent.constants import IntentType, ResponseType
from app.tools.monday_tool import MondayTool
from app.agents.alpha_agent.monday_generator import MondayGenerator
from app.core.config import Config
from app.core.exceptions import AgentException, ToolException, ProviderException
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()


class MondayAgentState(TypedDict):
    """State of the Monday chatbot agent"""
    messages: Annotated[List[BaseMessage], add_messages]
    user_input: str
    intent_analysis: Dict[str, Any]
    monday_data: Dict[str, Any]
    response: str
    action_taken: str
    error: Optional[str]
    context: Dict[str, Any]


class MondayChatbotAgent(ChatbotAgent):
    """Monday.com chatbot agent for task management and queries"""
    
    def __init__(self):
        super().__init__("MondayChatbotAgent")
        
        self.monday_client = None
        self.generator = None
        
        self._initialize_dependencies()
    
    def _initialize_dependencies(self) -> None:
        """Initialize required dependencies"""
        try:
            if not Config.MONDAY_API_TOKEN:
                raise AgentException("Monday API token is required")
            
            self.monday_client = MondayTool(api_token=Config.MONDAY_API_TOKEN)
            
            self.generator = MondayGenerator()
            
            self.logger.info("Dependencies initialized successfully")
            
        except Exception as e:
            raise AgentException(f"Failed to initialize dependencies: {str(e)}")
    
    def build_graph(self) -> StateGraph:
        """Build the agent's state graph"""
        try:
            workflow = StateGraph(MondayAgentState)
    
            workflow.add_node("analyze_input", self._analyze_input)
            workflow.add_node("fetch_monday_data", self._fetch_monday_data)
            workflow.add_node("generate_response", self._generate_response)
            workflow.add_node("send_notification", self._send_notification)
            workflow.add_node("handle_error", self._handle_error)
            
            workflow.set_entry_point("analyze_input")
            
            workflow.add_conditional_edges(
                "analyze_input",
                self._route_after_analysis,
                {
                    "fetch_data": "fetch_monday_data",
                    "generate_response": "generate_response",
                    "error": "handle_error"
                }
            )
            
            workflow.add_edge("fetch_monday_data", "generate_response")
            
            workflow.add_conditional_edges(
                "generate_response",
                self._route_after_response,
                {
                    "send_notification": "send_notification",
                    "end": END,
                }
            )
            
            workflow.add_edge("send_notification", END)
            workflow.add_edge("handle_error", END)
            
            return workflow.compile(checkpointer=self.memory)
            
        except Exception as e:
            raise AgentException(f"Failed to build agent graph: {str(e)}")
    
    def _analyze_input(self, state: MondayAgentState) -> MondayAgentState:
        """Analyze user input to determine intent and extract entities"""
        try:
            user_input = state.get("user_input", "")
            if not user_input:
                messages = state.get("messages", [])
                if messages and isinstance(messages[-1], HumanMessage):
                    user_input = messages[-1].content
            
            analysis = self.generator.analyze_user_message(
                user_input, 
                state.get("context", {})
            )
            
            state["intent_analysis"] = analysis
            state["user_input"] = user_input
            
            self.logger.info(f"Intent analysis completed: {analysis.get('intent', 'unknown')}")
            
        except (ProviderException, ToolException) as e:
            state["error"] = f"Error analyzing input: {str(e)}"
            self.logger.error(f"Error in _analyze_input: {e}")
        except Exception as e:
            state["error"] = f"Unexpected error analyzing input: {str(e)}"
            self.logger.error(f"Unexpected error in _analyze_input: {e}")
        
        return state
    
    def _fetch_monday_data(self, state: MondayAgentState) -> MondayAgentState:
        """Fetch relevant data from Monday.com based on intent"""
        try:
            analysis = state.get("intent_analysis", {})
            intent = analysis.get("intent", "")
            entities = analysis.get("entities", {})
            
            monday_data = {}
            self.monday_client.fetch_board_data()
            
            if intent in [IntentType.QUERY_STATUS.value, IntentType.DEADLINE_INQUIRY.value]:
                overdue = self.monday_client.get_overdue_tasks()
                upcoming = self.monday_client.get_upcoming_tasks()
                summary = self.monday_client.get_task_summary()
                
                monday_data["overdue_tasks"] = overdue
                monday_data["upcoming_tasks"] = upcoming
                monday_data["summary"] = summary
                
                mentioned_tasks = entities.get("tasks", [])
                if mentioned_tasks:
                    all_tasks = self.monday_client.get_all_task_details()
                    matching_tasks = []
                    
                    for task in all_tasks:
                        for task_name in mentioned_tasks:
                            if task_name.lower() in task["task"].lower():
                                matching_tasks.append(task)
                                break
                    
                    monday_data["matching_tasks"] = matching_tasks
            
            elif intent == IntentType.UPDATE_TASK.value:
                monday_data["update_capability"] = True
            
            else:
                self.logger.warning(f"Unsupported intent for data fetching: {intent}")
            
            state["monday_data"] = monday_data
            self.logger.info(f"Successfully fetched Monday data for intent: {intent}")
            
        except ToolException as e:
            state["error"] = f"Error fetching Monday data: {str(e)}"
            self.logger.error(f"Error in _fetch_monday_data: {e}")
        except Exception as e:
            state["error"] = f"Unexpected error fetching Monday data: {str(e)}"
            self.logger.error(f"Unexpected error in _fetch_monday_data: {e}")
        
        return state
    
    def _generate_response(self, state: MondayAgentState) -> MondayAgentState:
        """Generate response using the response generator"""
        try:
            user_input = state.get("user_input", "")
            analysis = state.get("intent_analysis", {})
            monday_data = state.get("monday_data", {})
            response = self.generator.generate_monday_response(
                user_input, 
                analysis, 
                monday_data
            )
            
            state["response"] = response
            messages = state.get("messages", [])
            messages.append(AIMessage(content=response))
            state["messages"] = messages
            
            self.logger.info("Response generated successfully")
            
        except ProviderException as e:
            state["error"] = f"Error generating response: {str(e)}"
            self.logger.error(f"Error in _generate_response: {e}")
        except Exception as e:
            state["error"] = f"Unexpected error generating response: {str(e)}"
            self.logger.error(f"Unexpected error in _generate_response: {e}")
        
        return state
    
    def _send_notification(self, state: MondayAgentState) -> MondayAgentState:
        """Send notification if required"""
        try:
            analysis = state.get("intent_analysis", {})
            response_type = analysis.get("response_type", "")
            
            if response_type == ResponseType.ACTIONABLE.value and Config.ENABLE_MONDAY_UPDATES:
                state["action_taken"] = "notification_sent"
                self.logger.info("Notification would be sent to Monday.com")
            else:
                state["action_taken"] = "no_notification_needed"
            
        except Exception as e:
            state["error"] = f"Error sending notification: {str(e)}"
            self.logger.error(f"Error in _send_notification: {e}")
        
        return state
    
    def _handle_error(self, state: MondayAgentState) -> MondayAgentState:
        """Handle errors gracefully"""
        error = state.get("error", "Unknown error")
        
        error_response = "I apologize, but I encountered an issue processing your request. Please try again later or contact an administrator."
        
        state["response"] = error_response
        
        messages = state.get("messages", [])
        messages.append(AIMessage(content=error_response))
        state["messages"] = messages
        
        self.logger.error(f"Error handled: {error}")
        
        return state
    
    def _route_after_analysis(self, 
                              state: MondayAgentState) -> str:
        """Route to next node after input analysis"""
        if state.get("error"):
            return "error"
        
        analysis = state.get("intent_analysis", {})
        intent = analysis.get("intent", "")
        
        if intent in [IntentType.QUERY_STATUS.value, IntentType.DEADLINE_INQUIRY.value, IntentType.UPDATE_TASK.value]:
            return "fetch_data"
        else:
            return "generate_response"
    
    def _route_after_response(self, 
                              state: MondayAgentState) -> str:
        """Route to next node after generating response"""
        if state.get("error"):
            return "end"
        
        analysis = state.get("intent_analysis", {})
        response_type = analysis.get("response_type", "")
        
        if response_type == ResponseType.ACTIONABLE.value:
            return "send_notification"
        else:
            return "end"
    
    def process_message(self, 
                        message: str, 
                        thread_id: str, 
                        context: Optional[Dict[str, Any]] = None) -> str:
        """Process a user message and return response"""
        try:
            self.ensure_initialized()

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
            
            final_state = self.graph.invoke(initial_state, config=config)
            
            response = final_state.get("response", "I apologize, but I couldn't process your request.")
            
            self.logger.info(f"Message processed successfully for thread: {thread_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to process message: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Please try again later."
