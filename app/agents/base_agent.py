from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from app.core.logger import Logger
from app.core.exceptions import AgentException


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = Logger.get_logger(f"{self.__class__.__name__}")
        self.memory = MemorySaver()
        self.graph = None
        self._initialized = False
    
    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Build the agent's state graph"""
        pass
    
    @abstractmethod
    def process_message(self, message: str, thread_id: str, 
                       context: Optional[Dict[str, Any]] = None) -> str:
        """Process a user message and return response"""
        pass
    
    def initialize(self) -> None:
        """Initialize the agent"""
        try:
            self.graph = self.build_graph()
            self._initialized = True
            self.logger.info(f"Agent {self.name} initialized successfully")
        except Exception as e:
            raise AgentException(f"Failed to initialize agent {self.name}: {str(e)}")
    
    def ensure_initialized(self) -> None:
        """Ensure the agent is initialized"""
        if not self._initialized:
            self.initialize()
    
    def is_healthy(self) -> bool:
        """Check if the agent is healthy and ready to use"""
        try:
            return self._initialized and self.graph is not None
        except Exception:
            return False
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.graph = None
        self._initialized = False
        self.logger.info(f"Agent {self.name} cleaned up")


class ChatbotAgent(BaseAgent):
    """Base class for chatbot agents"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.conversation_history: Dict[str, List[BaseMessage]] = {}
    
    # def get_conversation_history(self, thread_id: str) -> List[BaseMessage]:
    #     """Get conversation history for a thread"""
    #     return self.conversation_history.get(thread_id, [])
    
    # def add_to_conversation_history(self, thread_id: str, message: BaseMessage) -> None:
    #     """Add message to conversation history"""
    #     if thread_id not in self.conversation_history:
    #         self.conversation_history[thread_id] = []
        
    #     self.conversation_history[thread_id].append(message)
        
    #     # Keep only last 50 messages to prevent memory issues
    #     if len(self.conversation_history[thread_id]) > 50:
    #         self.conversation_history[thread_id] = self.conversation_history[thread_id][-50:]
    
    # def clear_conversation_history(self, thread_id: str) -> None:
    #     """Clear conversation history for a thread"""
    #     if thread_id in self.conversation_history:
    #         del self.conversation_history[thread_id]
    #         self.logger.info(f"Cleared conversation history for thread: {thread_id}")
