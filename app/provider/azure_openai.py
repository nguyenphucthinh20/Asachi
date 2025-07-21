"""
Azure OpenAI Client for generating responses and analyzing content
"""
from openai import AzureOpenAI
from typing import List, Dict, Any, Optional
import json
from app.core.config import Config

class AzureOpenAIClient:
    def __init__(self, api_key: str = None, endpoint: str = None, api_version: str = None):
        self.api_key = api_key or Config.AZURE_OPENAI_API_KEY
        self.endpoint = endpoint or Config.AZURE_OPENAI_ENDPOINT
        self.api_version = api_version or Config.AZURE_OPENAI_API_VERSION
        self.deployment_name = Config.AZURE_OPENAI_DEPLOYMENT_NAME
        
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint
        )
    
    def generate_overdue_reminder(self, overdue_tasks: List[Dict[str, Any]]) -> str:
        """Generate reminder message for overdue tasks"""
        
        # Nhóm tasks theo người
        grouped_tasks = {}
        for task in overdue_tasks:
            person = task["person"]
            if person not in grouped_tasks:
                grouped_tasks[person] = []
            grouped_tasks[person].append(task)
        
        # Tạo danh sách task
        all_tasks = []
        for person, tasks in grouped_tasks.items():
            for task in tasks:
                deadline = task["deadline"]
                if "-" in deadline:
                    day, month, year = deadline.split("-")[2], deadline.split("-")[1], deadline.split("-")[0]
                    deadline_formatted = f"{day}/{month}/{year}"
                else:
                    deadline_formatted = deadline
                
                all_tasks.append(f"- {task['task']} (hạn: {deadline_formatted}) do {person} đảm nhiệm, quá hạn {task['days_overdue']} ngày")
        
        task_summary = "\n".join(all_tasks)
        people_names = ", ".join(grouped_tasks.keys())
        
        prompt = f"""
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
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Tạo lời nhắc deadline thân thiện bằng tiếng Việt"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Chào {people_names}, bạn có {len(overdue_tasks)} nhiệm vụ quá hạn. Vui lòng hoàn thành sớm nhé!"

    def analyze_user_message(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze user message to determine intent and extract information"""
        
        prompt = f"""
        You are an AI assistant that analyzes user messages in a project management context.
        
        User message: "{message}"
        
        Context: {json.dumps(context or {}, ensure_ascii=False)}
        
        Analyze the message and determine:
        1. Intent (one of: query_status, update_task, general_question, deadline_inquiry, team_interaction)
        2. Entities mentioned (task names, dates, people, etc.)
        3. Required action (if any)
        4. Confidence level (0.0 to 1.0)
        
        Respond with a JSON object containing:
        {{
            "intent": "intent_name",
            "entities": {{
                "tasks": ["task1", "task2"],
                "dates": ["2024-01-01"],
                "people": ["person1"],
                "other": ["entity1"]
            }},
            "action": "description of required action",
            "confidence": 0.8,
            "response_type": "informational|actionable|conversational"
        }}
        
        Only return the JSON object, no additional text.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an AI assistant that analyzes user messages and returns structured JSON responses."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "intent": "general_question",
                    "entities": {},
                    "action": "provide general response",
                    "confidence": 0.5,
                    "response_type": "conversational"
                }
                
        except Exception as e:
            print(f"Error analyzing message: {e}")
            return {
                "intent": "general_question",
                "entities": {},
                "action": "provide general response",
                "confidence": 0.0,
                "response_type": "conversational"
            }
    
    def generate_response(self, user_message: str, analysis: Dict[str, Any], 
                         context_data: Dict[str, Any] = None) -> str:
        """Generate a response based on user message analysis and context"""
        
        intent = analysis.get('intent', 'general_question')
        entities = analysis.get('entities', {})
        
        context_str = ""
        if context_data:
            context_str = f"Available context data: {json.dumps(context_data, ensure_ascii=False, indent=2)}"
        
        prompt = f"""
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
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful project management assistant that responds in Vietnamese."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Xin lỗi, tôi gặp sự cố khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."
    
    def summarize_project_status(self, sumary_task):

        try:
            
            prompt = f"""
            Bạn là trợ lý quản lý dự án. Hãy tạo một tóm tắt ngắn gọn về trạng thái dự án hiện tại.
            
            THỐNG KÊ TỔNG QUAN:
            - Tổng số task: {sumary_task['total_tasks']}
            - Tổng số người tham gia: {sumary_task['total_people']}
            - Số task trễ deadline: {sumary_task['overdue_tasks']}
            - Số task sắp đến hạn: {sumary_task['upcoming_tasks']}
            
            
            Hãy tạo một tóm tắt bao gồm:
            - Tình trạng tổng thể của dự án
            - Các vấn đề cần quan tâm (nếu có)
            - Đánh giá mức độ rủi ro
            - Khuyến nghị hành động (nếu cần)
            
            Sử dụng tiếng Việt, phong cách chuyên nghiệp nhưng dễ hiểu.
            Giới hạn trong 4-5 câu.
            """
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý quản lý dự án chuyên nghiệp, tạo tóm tắt trạng thái dự án bằng tiếng Việt."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
                
        except Exception as e:
            print(f"Lỗi khi tạo tóm tắt: {e}")
            return "Không thể tạo tóm tắt trạng thái dự án lúc này."

