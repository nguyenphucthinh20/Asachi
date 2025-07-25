from app.provider.factory import llm_factory
from app.core.logger import Logger

class FriendlyResponseGenerator:
    def __init__(self):
        self.logger = Logger.get_logger(self.__class__.__name__)
        self.llm_client = llm_factory.get_default_provider()
    def generate_friendly_response(self, result: str) -> str:
        friendly_response_schema = {
            "friendly_answer": "A friendly, concise, and purposeful answer based on the result."
        }
        prompt = f"""Dựa trên kết quả sau, hãy tạo một câu trả lời thân thiện, ngắn gọn và đúng mục đích:
        {result}
        """
        try:
            response = self.llm_client.generate_structured_response(
                prompt=prompt,
                schema=friendly_response_schema,
                system_message="You are an AI assistant that generates friendly and concise answers based on provided results."
            )
            return response.get("friendly_answer", "Tôi chưa rõ câu hỏi của bạn, vui lòng hỏi chi tiết hơn.")
        except Exception as e:
            return f"Đã xảy ra lỗi khi tạo câu trả lời thân thiện: {e}"