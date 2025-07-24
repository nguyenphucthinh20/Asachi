from enum import Enum
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.core.config import Config
from app.tools.base import BaseAPITool
from app.core.exceptions import ToolException, ValidationException
from app.core.logger import Logger

DEFAULT_OVERDUE_DAYS = 7
DEFAULT_UPCOMING_DAYS = 7

class TaskStatus(Enum):
    """Task status enumeration"""
    APPROVED = "Approved"
    DONE = "Done"
    IN_PROGRESS = "In Progress"
    PENDING = "Pending"
    BLOCKED = "Blocked"


class MondayColumnIds:
    """Monday.com column IDs"""
    PERSON = "person"
    DATE = "date4"
    STATUS = "status"
    CLIENT = "dropdown_mksnbmk2"
    MIRO_LINK = "link_mksnj6fc"
    DRIVE_LINK = "link_mksn5w3"
    FRAMEIO_LINK = "link_mksnvt1d"
    NOTES = "long_text_mksn8vr6"
    PRIORITY = "text_mksnh90q"

class MondayTool(BaseAPITool):
    """Monday.com task management tool"""
    
    def __init__(self, api_token: str, board_id: int = 2039779333):
        super().__init__("MondayTool", api_token, "https://api.monday.com/v2")
        self.board_id = board_id
        self.logger = Logger.get_logger(self.__class__.__name__)
        self._board_data = None
        self._last_fetch_time = None
        self._cache_duration = timedelta(minutes=5)  # Cache for 5 minutes
    
    def _build_headers(self) -> Dict[str, str]:
        """Build API headers for Monday.com"""
        return {
            "Authorization": self.api_token,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str = "", **kwargs) -> Any:
        """Make API request to Monday.com"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Monday.com API request failed: {str(e)}")
            raise ToolException(f"Monday.com API request failed: {str(e)}")
    
    def initialize(self) -> None:
        """Initialize the Monday.com tool"""
        try:
            self.fetch_board_data()
            self.logger.info("Monday.com tool initialized successfully")
        except Exception as e:
            raise ToolException(f"Failed to initialize Monday.com tool: {str(e)}")
    
    def is_healthy(self) -> bool:
        """Check if the Monday.com API is accessible"""
        try:
            query = "{ me { id } }"
            response = self._make_request("POST", json={"query": query})
            return "data" in response and "me" in response["data"]
        except Exception as e:
            self.logger.error(f"Monday.com health check failed: {str(e)}")
            return False
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self._board_data = None
        self._last_fetch_time = None
        self.logger.info("Monday.com tool cleaned up")
    
    def fetch_board_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch board data from Monday.com API with caching"""
        try:
            current_time = datetime.now()
            
            # Use cached data if available and not expired
            if (not force_refresh and self._board_data and self._last_fetch_time and 
                current_time - self._last_fetch_time < self._cache_duration):
                return self._board_data
            
            query = self._build_board_query()
            data = {"query": query}
            
            response = self._make_request("POST", json=data)
            
            if "errors" in response:
                raise ToolException(f"Monday.com API returned errors: {response['errors']}")
            
            self._board_data = response
            self._last_fetch_time = current_time
            
            self.logger.info(f"Successfully fetched board data for board {self.board_id}")
            return self._board_data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch board data: {str(e)}")
            raise ToolException(f"Failed to fetch board data: {str(e)}")
    
    def get_overdue_tasks(self, overdue_days: int = DEFAULT_OVERDUE_DAYS) -> List[Dict[str, Any]]:
        """Get list of overdue tasks"""
        try:
            
            self.ensure_initialized()
            if not self._board_data:
                self.fetch_board_data()
            
            today = datetime.today().date()
            overdue_tasks = []
            
            for board in self._board_data["data"]["boards"]:
                group_map = {g["id"]: g["title"] for g in board["groups"]}
                
                for item in board["items_page"]["items"]:
                    task_data = self._extract_task_data(item, group_map)
                    
                    if task_data["deadline"]:
                        try:
                            item_date = datetime.strptime(task_data["deadline"], "%Y-%m-%d").date()
                            days_overdue = (today - item_date).days
                            
                            if (days_overdue > overdue_days and 
                                task_data["status"] not in [TaskStatus.APPROVED.value, TaskStatus.DONE.value]):
                                
                                task_data["days_overdue"] = days_overdue
                                overdue_tasks.append(task_data)
                                
                        except ValueError as e:
                            self.logger.warning(f"Invalid date format for task {task_data['task']}: {task_data['deadline']}")
            
            self.logger.info(f"Found {len(overdue_tasks)} overdue tasks")
            return overdue_tasks
            
        except Exception as e:
            self.logger.error(f"Failed to get overdue tasks: {str(e)}")
            raise ToolException(f"Failed to get overdue tasks: {str(e)}")
    
    def get_upcoming_tasks(self, days_ahead: int = DEFAULT_UPCOMING_DAYS) -> List[Dict[str, Any]]:
        """Get list of upcoming tasks"""
        try:
            
            self.ensure_initialized()
            if not self._board_data:
                self.fetch_board_data()
            
            today = datetime.today().date()
            upcoming_tasks = []
            
            for board in self._board_data["data"]["boards"]:
                group_map = {g["id"]: g["title"] for g in board["groups"]}
                
                for item in board["items_page"]["items"]:
                    task_data = self._extract_task_data(item, group_map)
                    
                    if task_data["deadline"]:
                        try:
                            item_date = datetime.strptime(task_data["deadline"], "%Y-%m-%d").date()
                            days_left = (item_date - today).days
                            
                            if (0 <= days_left <= days_ahead and 
                                task_data["status"] not in [TaskStatus.APPROVED.value, TaskStatus.DONE.value]):
                                
                                task_data["days_left"] = days_left
                                upcoming_tasks.append(task_data)
                                
                        except ValueError as e:
                            self.logger.warning(f"Invalid date format for task {task_data['task']}: {task_data['deadline']}")
            
            self.logger.info(f"Found {len(upcoming_tasks)} upcoming tasks")
            return upcoming_tasks
            
        except Exception as e:
            self.logger.error(f"Failed to get upcoming tasks: {str(e)}")
            raise ToolException(f"Failed to get upcoming tasks: {str(e)}")
    
    def get_all_task_details(self) -> List[Dict[str, Any]]:
        """Get comprehensive details for all tasks"""
        try:
            self.ensure_initialized()
            if not self._board_data:
                self.fetch_board_data()
            
            all_tasks = []
            
            for board in self._board_data["data"]["boards"]:
                group_map = {g["id"]: g["title"] for g in board["groups"]}
                
                for item in board["items_page"]["items"]:
                    task_data = self._extract_comprehensive_task_data(item, group_map)
                    all_tasks.append(task_data)
            
            self.logger.info(f"Retrieved details for {len(all_tasks)} tasks")
            return all_tasks
            
        except Exception as e:
            self.logger.error(f"Failed to get all task details: {str(e)}")
            raise ToolException(f"Failed to get all task details: {str(e)}")
    
    def get_task_summary(self, overdue_days: int = 3, upcoming_days: int = DEFAULT_UPCOMING_DAYS) -> Dict[str, Any]:
        """Get task summary statistics"""
        try:
            
            self.ensure_initialized()
            if not self._board_data:
                self.fetch_board_data()
            
            today = datetime.today().date()
            total_tasks = 0
            people_set = set()
            overdue_count = 0
            upcoming_count = 0
            
            for board in self._board_data["data"]["boards"]:
                for item in board["items_page"]["items"]:
                    total_tasks += 1
                    
                    person = None
                    date_str = None
                    status = None
                    
                    # Extract task information
                    for col in item["column_values"]:
                        if col["id"] == MondayColumnIds.PERSON:
                            person = col["text"]
                        elif col["id"] == MondayColumnIds.DATE:
                            date_str = col["text"]
                        elif col["id"] == MondayColumnIds.STATUS:
                            status = col["text"]
                    
                    # Count unique people
                    if person:
                        people_set.add(person)
                    
                    # Count overdue and upcoming tasks
                    if date_str:
                        try:
                            item_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            days_diff = (today - item_date).days
                            
                            # Only count incomplete tasks
                            if status not in [TaskStatus.APPROVED.value, TaskStatus.DONE.value]:
                                if days_diff > overdue_days:
                                    overdue_count += 1
                                elif -upcoming_days <= days_diff <= 0:
                                    upcoming_count += 1
                                    
                        except ValueError:
                            continue
            
            summary = {
                "total_tasks": total_tasks,
                "total_people": len(people_set),
                "overdue_tasks": overdue_count,
                "upcoming_tasks": upcoming_count
            }
            
            self.logger.info(f"Generated task summary: {summary}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get task summary: {str(e)}")
            raise ToolException(f"Failed to get task summary: {str(e)}")
    
    def _build_board_query(self) -> str:
        """Build GraphQL query for board data"""
        return f"""
        {{
          boards(ids: {self.board_id}) {{
            name
            groups {{
              id
              title
            }}
            items_page {{
              items {{
                id
                name
                group {{
                  id
                }}
                column_values {{
                  id
                  text
                }}
              }}
            }}
          }}
        }}
        """
    
    def _extract_task_data(self, item: Dict[str, Any], group_map: Dict[str, str]) -> Dict[str, Any]:
        """Extract basic task data from Monday.com item"""
        task_data = {
            "task": item["name"],
            "group": group_map.get(item["group"]["id"], ""),
            "person": None,
            "deadline": None,
            "status": None
        }
        
        for col in item["column_values"]:
            if col["id"] == MondayColumnIds.PERSON:
                task_data["person"] = col["text"]
            elif col["id"] == MondayColumnIds.DATE:
                task_data["deadline"] = col["text"]
            elif col["id"] == MondayColumnIds.STATUS:
                task_data["status"] = col["text"]
        
        return task_data
    
    def _extract_comprehensive_task_data(self, item: Dict[str, Any], group_map: Dict[str, str]) -> Dict[str, Any]:
        """Extract comprehensive task data from Monday.com item"""
        task_data = {
            "task": item["name"],
            "group": group_map.get(item["group"]["id"], ""),
            "person": None,
            "deadline": None,
            "status": None,
            "client": None,
            "miro_link": None,
            "drive_link": None,
            "frameio_link": None,
            "notes": None,
            "priority": None,
        }
        
        column_mapping = {
            MondayColumnIds.PERSON: "person",
            MondayColumnIds.DATE: "deadline",
            MondayColumnIds.STATUS: "status",
            MondayColumnIds.CLIENT: "client",
            MondayColumnIds.MIRO_LINK: "miro_link",
            MondayColumnIds.DRIVE_LINK: "drive_link",
            MondayColumnIds.FRAMEIO_LINK: "frameio_link",
            MondayColumnIds.NOTES: "notes",
            MondayColumnIds.PRIORITY: "priority"
        }
        
        for col in item["column_values"]:
            if col["id"] in column_mapping:
                task_data[column_mapping[col["id"]]] = col["text"]
        
        return task_data
