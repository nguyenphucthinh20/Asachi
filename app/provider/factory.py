from typing import Optional
from app.provider.base import BaseAIProvider
from app.provider.azure_openai import AzureOpenAIClient
from app.provider.gemini import GeminiClient
from app.core.config import Config
from app.core.exceptions import ProviderException
from app.core.logger import Logger


class LLMProviderType:
    """LLM Provider type constants"""
    AZURE_OPENAI = "azure_openai"
    GEMINI = "gemini"


class LLMFactory:
    """Factory class for creating LLM providers"""
    
    _instance = None
    _providers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMFactory, cls).__new__(cls)
            cls._instance.logger = Logger.get_logger(cls.__name__)
        return cls._instance
    
    def get_provider(self, provider_type: Optional[str] = None) -> BaseAIProvider:
        """Get LLM provider instance"""
        provider_type = provider_type or Config.LLM_PROVIDER
        
        if not provider_type:
            raise ProviderException("LLM provider type is not configured")
        
        # Return cached provider if exists
        if provider_type in self._providers:
            return self._providers[provider_type]
        
        # Create new provider instance
        provider = self._create_provider(provider_type)
        self._providers[provider_type] = provider
        
        self.logger.info(f"Created LLM provider: {provider_type}")
        return provider
    
    def _create_provider(self, provider_type: str) -> BaseAIProvider:
        """Create provider instance based on type"""
        if provider_type == LLMProviderType.AZURE_OPENAI:
            return AzureOpenAIClient()
        elif provider_type == LLMProviderType.GEMINI:
            return GeminiClient()
        else:
            raise ProviderException(f"Unsupported LLM provider type: {provider_type}")
    
    def get_default_provider(self) -> BaseAIProvider:
        """Get the default configured provider"""
        return self.get_provider()

# Global factory instance
llm_factory = LLMFactory()
