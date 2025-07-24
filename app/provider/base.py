"""
Base provider interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseProvider(ABC):
    """Abstract base class for all providers"""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the provider"""
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if the provider is healthy and ready to use"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup resources"""
        pass


class BaseAIProvider(BaseProvider):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text based on prompt"""
        pass
