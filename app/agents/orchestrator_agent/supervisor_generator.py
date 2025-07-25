from app.provider.factory import llm_factory
from app.core.logger import Logger

class SupervisorGenerator:
    def __init__(self):
        self.logger = Logger.get_logger(self.__class__.__name__)
        self.llm_client = llm_factory.get_default_provider()

    def decide_next_agent(self, question: str) -> str:
        decision_schema = {
            "next_agent": {"type": "string", "enum": ["alpha", "beta", "general"]}
        }
        prompt = f"""
You are a supervisor agent. You need to decide which sub-agent (alpha or beta) should handle the user's request.

Alpha agent handles:
- Project progress
- Deadline tracking
- Task delay detection
- Task assignments and team member workloads
- All queries related to Monday.com or project/task management

Beta agent handles:
- Any question involving uploaded Excel files, spreadsheets, CSVs, or image-based tables

Respond with:
- 'alpha' if the request is about deadlines, project progress, team task status, or uses Monday.com
- 'beta' if the request is about analyzing data in Excel, CSV, or table/image files
- 'general' if it's not related to either

Here is the user's question: {question}
"""
        try:
            response = self.llm_client.generate_structured_response(
                prompt=prompt,
                schema=decision_schema,
                system_message="You are an AI assistant that decides the next agent based on the user's request."
            )
            return response.get("next_agent", "general")
        except Exception as e:
            self.logger.error(f"Error deciding next agent: {e}")
            return "general"

    def generate_general_response(self, question: str) -> str:
        general_response_schema = {
            "friendly_answer": "A friendly, helpful, and conversational response to the user's question."
        }
        prompt = f"""Hãy trả lời câu hỏi sau một cách thân thiện, hữu ích và tự nhiên như một trợ lý AI:
        {question}
        """
        try:
            response = self.llm_client.generate_structured_response(
                prompt=prompt,
                schema=general_response_schema,
                system_message="You are a friendly AI assistant that provides helpful and conversational responses."
            )
            return response.get("friendly_answer", "đây là câu hỏi không liên quan đến dự án")
        except Exception as e:
            self.logger.error(f"Error generating general response: {e}")
            return "Tôi xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn. Vui lòng thử lại sau."


