import google as genai
from typing import List, Dict, Any, Optional
import json
from app.core.config import Config
from app.provider.base import BaseAIProvider
from app.core.exceptions import ProviderException, ValidationException
from app.core.logger import Logger


class GeminiClient(BaseAIProvider):
    """Google Gemini client for text generation and analysis"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.logger = Logger.get_logger(self.__class__.__name__)
        
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model_name or Config.GEMINI_MODEL_NAME or "gemini-1.5-flash"
        
        self._validate_configuration()
        self.client = None
        self.model = None
        self.initialize()
    
    def _validate_configuration(self) -> None:
        """Validate Gemini configuration"""
        if not self.api_key:
            raise ValidationException("Gemini API key is required")
    
    def initialize(self) -> None:
        """Initialize the Gemini client"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            self.logger.info(f"Gemini client initialized successfully with model: {self.model_name}")
        except Exception as e:
            raise ProviderException(f"Failed to initialize Gemini client: {str(e)}")
    
    def is_healthy(self) -> bool:
        """Check if the Gemini client is healthy"""
        try:
            if not self.model:
                return False
            
            # Simple health check by making a minimal request
            response = self.model.generate_content("test")
            return response is not None
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.model = None
        self.logger.info("Gemini client cleaned up")
    
    def generate_text(self, prompt: str, max_tokens: int = Config.DEFAULT_MAX_TOKENS, 
                     temperature: float = Config.DEFAULT_TEMPERATURE, 
                     system_message: Optional[str] = None, **kwargs) -> str:
        """Generate text based on prompt"""
        try:
            
            # Combine system message with prompt if provided
            full_prompt = prompt
            if system_message:
                full_prompt = f"System: {system_message}\n\nUser: {prompt}"
            
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            if response.text:
                return response.text.strip()
            else:
                raise ProviderException("Empty response from Gemini")
            
        except Exception as e:
            self.logger.error(f"Text generation failed: {str(e)}")
            raise ProviderException(f"Failed to generate text: {str(e)}")
    
    def generate_response(self, user_message: str, context: Optional[Dict[str, Any]] = None,
                         system_instructions: Optional[str] = None,
                         response_format: Optional[str] = None) -> str:
        """Generate a response based on user message and context"""
        try:
            prompt = self._build_response_prompt(user_message, context or {}, response_format)
            
            system_message = system_instructions or "You are a helpful AI assistant."
            
            return self.generate_text(
                prompt=prompt,
                system_message=system_message,
                max_tokens=400,
                temperature=0.7
            )
            
        except Exception as e:
            self.logger.error(f"Response generation failed: {str(e)}")
            return "I apologize, but I encountered an issue processing your request. Please try again later."
    
    def generate_structured_response(self, prompt: str, schema: Dict[str, Any],
                                   system_message: Optional[str] = None) -> Dict[str, Any]:
        """Generate a structured response based on a schema"""
        try: 
            structured_prompt = f"""
            {prompt}
            
            Please respond with a JSON object that follows this schema:
            {json.dumps(schema, indent=2)}
            
            Only return the JSON object, no additional text.
            """
            
            response_text = self.generate_text(
                prompt=structured_prompt,
                system_message=system_message or "You are an AI that returns structured JSON responses.",
                temperature=0.3
            )
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse structured response")
                return {}
                
        except Exception as e:
            self.logger.error(f"Structured response generation failed: {str(e)}")
            raise ProviderException(f"Failed to generate structured response: {str(e)}")
    
    def _build_response_prompt(self, user_message: str, context: Dict[str, Any],
                              response_format: Optional[str] = None) -> str:
        """Build prompt for response generation"""
        context_str = ""
        if context:
            context_str = f"Available context: {json.dumps(context, ensure_ascii=False, indent=2)}"
        
        format_instruction = ""
        if response_format:
            format_instruction = f"Response format: {response_format}"
        
        return f"""
        User message: "{user_message}"
        
        {context_str}
        
        {format_instruction}
        
        Generate a helpful and appropriate response based on the user message and available context.
        """
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Get default analysis when parsing fails"""
        return {
            "intent": "general_question",
            "entities": {},
            "confidence": 0.5,
            "summary": "Unable to analyze text"
        }
