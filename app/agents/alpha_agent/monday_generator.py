from typing import List, Dict, Any, Optional
from app.provider.factory import llm_factory
from app.core.logger import Logger
from app.agents.alpha_agent.constants import IntentType, ResponseType
import json


class MondayGenerator:
    """Handles Monday-specific response generation and analysis"""
    
    def __init__(self):
        self.logger = Logger.get_logger(self.__class__.__name__)
        self.llm_client = llm_factory.get_default_provider()
    
    def analyze_user_message(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze user message to determine intent and extract information for Monday context"""
        
        analysis_schema = {
            "intent": f"one of: {', '.join([intent.value for intent in IntentType])}",
            "entities": {
                "tasks": ["task1", "task2"],
                "dates": ["2024-01-01"],
                "people": ["person1"],
                "other": ["entity1"]
            },
            "action": "description of required action",
            "confidence": "float between 0.0 and 1.0",
            "response_type": f"{ResponseType.INFORMATIONAL.value}|{ResponseType.ACTIONABLE.value}|{ResponseType.CONVERSATIONAL.value}"
        }
        
        prompt = f"""
        You are an AI assistant that analyzes user messages in a project management context.
        
        User message: "{message}"
        
        Context: {json.dumps(context or {}, ensure_ascii=False)}
        
        Analyze the message and determine:
        1. Intent (one of: {', '.join([intent.value for intent in IntentType])})
        2. Entities mentioned (task names, dates, people, etc.)
        3. Required action (if any)
        4. Confidence level (0.0 to 1.0)
        5. Response type
        """
        
        try:
            return self.llm_client.generate_structured_response(
                prompt=prompt,
                schema=analysis_schema,
                system_message="You are an AI assistant that analyzes user messages and returns structured JSON responses."
            )
        except Exception as e:
            self.logger.error(f"Failed to analyze user message: {str(e)}")
            return self._get_default_monday_analysis()   
    
    def generate_monday_response(self, user_message: str, analysis: Dict[str, Any], 
                               context_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a response based on user message analysis and Monday context"""
        try:
            intent = analysis.get('intent', IntentType.GENERAL_QUESTION.value)
            entities = analysis.get('entities', {})
            
            prompt = self._build_monday_response_prompt(user_message, intent, entities, context_data or {})
            
            system_message = "You are a helpful project management assistant for a Monday.com workspace that responds in Vietnamese."
            
            return self.llm_client.generate_text(
                prompt=prompt,
                system_message=system_message,
                max_tokens=400,
                temperature=0.7
            )
            
        except Exception as e:
            self.logger.error(f"Monday response generation failed: {str(e)}")
            return "Xin lỗi, tôi gặp sự cố khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."
    
    def _build_reminder_prompt(self, people_names: str, task_summary: str) -> str:
        """Build prompt for overdue task reminder"""
        return f"""
        Tạo lời nhắc deadline bằng tiếng Việt:
        
        Người có task quá hạn: {people_names}
        Các task quá hạn:
        {task_summary}
        
        Yêu cầu:
        - Chào tên từng người
        - Nhắc nhẹ có task quá hạn
        - Liệt kê task với deadline, người làm và số ngày quá hạn
        - Kết thúc động viên
        - Giọng văn thân thiện, tự nhiên
        - Tối đa 4-5 câu
        """
    
    def _build_monday_response_prompt(self, user_message: str, intent: str, entities: Dict[str, Any], 
                                    context_data: Dict[str, Any]) -> str:
        """Build prompt for Monday-specific response generation"""
        context_str = f"Available context data: {json.dumps(context_data, ensure_ascii=False, indent=2)}" if context_data else ""
        
        return f"""
        You are a helpful project management assistant for a Monday.com workspace.
        
        User message: "{user_message}"
        Detected intent: {intent}
        Extracted entities: {json.dumps(entities, ensure_ascii=False)}
        
        {context_str}
        
        Based on the intent and available context, generate a helpful response in Vietnamese.
        
        Guidelines:
        - Be friendly and professional
        - If asking about specific tasks/deadlines, provide specific information from context
        - If context is insufficient, ask clarifying questions
        - For general questions, provide helpful guidance
        - Keep responses concise but informative
        - Use Vietnamese language naturally
        
        Generate only the response message, no additional text.
        """
    
    
    def _get_default_monday_analysis(self) -> Dict[str, Any]:
        """Get default analysis when parsing fails"""
        return {
            "intent": IntentType.GENERAL_QUESTION.value,
            "entities": {},
            "action": "provide general response",
            "confidence": 0.5,
            "response_type": ResponseType.CONVERSATIONAL.value
        }
