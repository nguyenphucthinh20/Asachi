from typing import Annotated, TypedDict, List, Optional
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from app.agents.delta_agent.box_agent import BoxAgent
from app.agents.alpha_agent.monday_agent import MondayChatbotAgent
from .supervisor_generator import SupervisorGenerator

memory = MemorySaver()

class SupervisorAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    question: str
    next_agent: str
    response: str
    error: Optional[str]

class SupervisorAgent:
    def __init__(self):
        self.alpha_agent = BoxAgent()
        self.beta_agent = MondayChatbotAgent()
        self.generator = SupervisorGenerator()
        self.graph = self.build_graph()

    def build_graph(self) -> StateGraph:
        workflow = StateGraph(SupervisorAgentState)

        workflow.add_node("analyze_request", self._analyze_request)
        workflow.add_node("call_alpha", self._call_alpha)
        workflow.add_node("call_beta", self._call_beta)
        workflow.add_node("call_general", self._call_general)
        workflow.add_node("handle_error", self._handle_error)

        workflow.set_entry_point("analyze_request")

        workflow.add_conditional_edges(
            "analyze_request",
            self._route_after_analysis,
            {
                "alpha": "call_alpha",
                "beta": "call_beta",
                "general": "call_general",
                "error": "handle_error"
            }
        )

        workflow.add_edge("call_alpha", END)
        workflow.add_edge("call_beta", END)
        workflow.add_edge("call_general", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile(checkpointer=memory)

    def _analyze_request(self, state: SupervisorAgentState) -> SupervisorAgentState:
        try:
            user_input = state.get("question", "")
            if not user_input:
                messages = state.get("messages", [])
                if messages and isinstance(messages[-1], HumanMessage):
                    user_input = messages[-1].content

            state["question"] = user_input
            next_agent = self.generator.decide_next_agent(user_input)
            
            # Fix: Đảm bảo next_agent luôn là string
            if isinstance(next_agent, dict):
                next_agent = next_agent.get("type", "general")
            elif not isinstance(next_agent, str):
                next_agent = str(next_agent) if next_agent else "general"
            
            # Validate next_agent có trong danh sách hợp lệ
            valid_agents = ["alpha", "beta", "general"]
            if next_agent not in valid_agents:
                print(f"WARNING: Invalid next_agent '{next_agent}', defaulting to 'general'")
                next_agent = "general"
            
            state["next_agent"] = next_agent
            print(f"DEBUG: Set next_agent to: {next_agent}")

        except Exception as e:
            print(f"ERROR in _analyze_request: {str(e)}")
            state["error"] = f"Error analyzing request: {str(e)}"

        return state

    def _call_alpha(self, state: SupervisorAgentState) -> SupervisorAgentState:
        try:
            question = state.get("question", "")
            thread_id = self._get_thread_id_from_state(state)
            
            response = self.alpha_agent.process_message(question, thread_id)
            state["response"] = response

            messages = state.get("messages", [])
            messages.append(AIMessage(content=response))
            state["messages"] = messages

        except Exception as e:
            print(f"ERROR in _call_alpha: {str(e)}")
            state["error"] = f"Error calling alpha agent: {str(e)}"

        return state

    def _call_beta(self, state: SupervisorAgentState) -> SupervisorAgentState:
        try:
            question = state.get("question", "")
            thread_id = self._get_thread_id_from_state(state)
            
            response = self.beta_agent.process_message(question, thread_id)
            state["response"] = response

            messages = state.get("messages", [])
            messages.append(AIMessage(content=response))
            state["messages"] = messages

        except Exception as e:
            print(f"ERROR in _call_beta: {str(e)}")
            state["error"] = f"Error calling beta agent: {str(e)}"

        return state

    def _call_general(self, state: SupervisorAgentState) -> SupervisorAgentState:
        try:
            question = state.get("question", "")
            
            response = self.generator.generate_general_response(question)
            state["response"] = response

            messages = state.get("messages", [])
            messages.append(AIMessage(content=response))
            state["messages"] = messages

        except Exception as e:
            print(f"ERROR in _call_general: {str(e)}")
            state["error"] = f"Error calling general response generator: {str(e)}"

        return state

    def _handle_error(self, state: SupervisorAgentState) -> SupervisorAgentState:
        error = state.get("error", "Unknown error")
        print(f"HANDLING ERROR: {error}")
        
        error_response = f"Tôi xin lỗi, nhưng tôi gặp sự cố khi xử lý yêu cầu của bạn: {error}. Vui lòng thử lại sau."
        
        state["response"] = error_response
        
        messages = state.get("messages", [])
        messages.append(AIMessage(content=error_response))
        state["messages"] = messages
        
        return state

    def _route_after_analysis(self, state: SupervisorAgentState) -> str:
        # Debug thông tin state
        print(f"DEBUG: Full state keys: {list(state.keys())}")
        print(f"DEBUG: state error: {state.get('error')}")
        print(f"DEBUG: state next_agent: {state.get('next_agent')} (type: {type(state.get('next_agent'))})")
        
        # Kiểm tra lỗi trước
        if state.get("error"):
            print("DEBUG: Routing to error handler")
            return "error"
        
        # Lấy next_agent và xử lý
        next_agent = state.get("next_agent", "general")
        
        # Fix: Xử lý trường hợp next_agent là dict
        if isinstance(next_agent, dict):
            next_agent = next_agent.get("type", "general")
            print(f"DEBUG: Extracted from dict: {next_agent}")
        
        # Đảm bảo next_agent là string và hợp lệ
        if not isinstance(next_agent, str):
            next_agent = str(next_agent) if next_agent else "general"
            print(f"DEBUG: Converted to string: {next_agent}")
        
        # Validate giá trị hợp lệ
        valid_routes = ["alpha", "beta", "general", "error"]
        if next_agent not in valid_routes:
            print(f"WARNING: Invalid route '{next_agent}', available routes: {valid_routes}")
            next_agent = "general"
        
        print(f"DEBUG: Final routing decision: {next_agent}")
        return next_agent

    def _get_thread_id_from_state(self, state: SupervisorAgentState) -> str:
        return getattr(state, '_thread_id', 'default')

    def process_message(self, question: str, thread_id: str) -> str:
        # try:
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "question": question,
            "next_agent": "",
            "response": "",
            "error": None
        }
        
        print(f"DEBUG: Processing message: '{question}' with thread_id: {thread_id}")
        
        final_state = self.graph.invoke(initial_state, config=config)
        
        response = final_state.get("response", "Tôi xin lỗi, nhưng tôi không thể xử lý yêu cầu của bạn.")
        
        print(f"DEBUG: Final response: {response}")
        return response
            
        # except Exception as e:
        #     error_msg = f"Error processing message supervisor agent: {str(e)}"
        #     print(error_msg)
        #     return "Tôi xin lỗi, nhưng tôi gặp lỗi khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."