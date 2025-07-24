from typing import Optional, Any


class AsachiBaseException(Exception):
    """Base exception for all Asachi application errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Any] = None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


class AgentException(AsachiBaseException):
    """Exception raised by agent operations"""
    pass


class ToolException(AsachiBaseException):
    """Exception raised by tool operations"""
    pass


class ProviderException(AsachiBaseException):
    """Exception raised by provider operations"""
    pass


class ConfigurationException(AsachiBaseException):
    """Exception raised for configuration errors"""
    pass


class ValidationException(AsachiBaseException):
    """Exception raised for validation errors"""
    pass
