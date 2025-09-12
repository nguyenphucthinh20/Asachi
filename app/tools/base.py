"""
Base tool interface
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(self, name: str):
        self.name = name
        self._initialized = False
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the tool"""
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if the tool is healthy and ready to use"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup resources"""
        pass
    
    def ensure_initialized(self) -> None:
        """Ensure the tool is initialized"""
        if not self._initialized:
            self.initialize()
            self._initialized = True


class BaseAPITool(BaseTool):
    """Abstract base class for API-based tools"""
    
    def __init__(self, name: str, api_token: str, base_url: str):
        super().__init__(name)
        self.api_token = api_token
        self.base_url = base_url
        self.headers = self._build_headers()
    
    @abstractmethod
    def _build_headers(self) -> Dict[str, str]:
        """Build API headers"""
        pass
    
    @abstractmethod
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request"""
        pass
