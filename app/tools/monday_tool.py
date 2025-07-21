import requests
import json
from datetime import datetime, timedelta

class MondayTaskManager:
    def __init__(self, api_token, board_id=2039779333):
        self.api_url = "https://api.monday.com/v2"
        self.headers = {"Authorization": api_token}
        self.board_id = board_id
        self.data = None
    
    def fetch_board_data(self):
        """Lấy dữ liệu board từ Monday.com API"""
        query = f"""
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
        
        data = {'query': query}
        response = requests.post(url=self.api_url, json=data, headers=self.headers)
        self.data = response.json()
        return self.data
    
    def print_response(self):
        """In toàn bộ response để kiểm tra"""
        if self.data:
            print(json.dumps(self.data, indent=2))
        else:
            print("Chưa có dữ liệu. Hãy gọi fetch_board_data() trước.")
    
    def get_overdue_tasks(self, overdue_days=7):
        """
        Lấy danh sách task trễ hơn 'overdue_days' ngày.
        Trả về danh sách dict: task name, person, deadline, status, group, days_overdue.
        """
        if not self.data:
            raise ValueError("Chưa có dữ liệu. Hãy gọi fetch_board_data() trước.")
        
        today = datetime.today().date()
        overdue_tasks = []

        for board in self.data["data"]["boards"]:
            # Tạo map group ID => title
            group_map = {g["id"]: g["title"] for g in board["groups"]}
            
            for item in board["items_page"]["items"]:
                person = None
                date_str = None
                status = None
                group_id = item["group"]["id"]
                group_title = group_map.get(group_id, "")

                for col in item["column_values"]:
                    if col["id"] == "person":
                        person = col["text"]
                    elif col["id"] == "date4":
                        date_str = col["text"]
                    elif col["id"] == "status":
                        status = col["text"]

                if date_str:
                    try:
                        item_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        days_overdue = (today - item_date).days
                        
                        if days_overdue > overdue_days and status not in ["Approved", "Done"]:
                            overdue_tasks.append({
                                "task": item["name"],
                                "person": person,
                                "deadline": str(item_date),
                                "status": status,
                                "group": group_title,
                                "days_overdue": days_overdue
                            })
                    except ValueError:
                        pass

        return overdue_tasks
    
    def get_all_task_details(self):
        """
        Lấy toàn bộ thông tin đầy đủ của từng task để đưa vào LLM tóm tắt.
        Trả về danh sách dict chi tiết.
        """
        if not self.data:
            raise ValueError("Chưa có dữ liệu. Hãy gọi fetch_board_data() trước.")
        
        all_tasks = []

        for board in self.data["data"]["boards"]:
            group_map = {g["id"]: g["title"] for g in board["groups"]}
            
            for item in board["items_page"]["items"]:
                task_info = {
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

                for col in item["column_values"]:
                    if col["id"] == "person":
                        task_info["person"] = col["text"]
                    elif col["id"] == "date4":
                        task_info["deadline"] = col["text"]
                    elif col["id"] == "status":
                        task_info["status"] = col["text"]
                    elif col["id"] == "dropdown_mksnbmk2":
                        task_info["client"] = col["text"]
                    elif col["id"] == "link_mksnj6fc":
                        task_info["miro_link"] = col["text"]
                    elif col["id"] == "link_mksn5w3":
                        task_info["drive_link"] = col["text"]
                    elif col["id"] == "link_mksnvt1d":
                        task_info["frameio_link"] = col["text"]
                    elif col["id"] == "long_text_mksn8vr6":
                        task_info["notes"] = col["text"]
                    elif col["id"] == "text_mksnh90q":
                        task_info["priority"] = col["text"]

                all_tasks.append(task_info)

        return all_tasks

    def get_upcoming_tasks(self, days_ahead=7):
        if not self.data:
            raise ValueError("Chưa có dữ liệu. Hãy gọi fetch_board_data() trước.")
        
        today = datetime.today().date()
        upcoming_tasks = []

        for board in self.data["data"]["boards"]:
            group_map = {g["id"]: g["title"] for g in board["groups"]}

            for item in board["items_page"]["items"]:
                person = None
                date_str = None
                status = None
                group_id = item["group"]["id"]
                group_title = group_map.get(group_id, "")

                for col in item["column_values"]:
                    if col["id"] == "person":
                        person = col["text"]
                    elif col["id"] == "date4":
                        date_str = col["text"]
                    elif col["id"] == "status":
                        status = col["text"]

                if date_str:
                    try:
                        item_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        days_left = (item_date - today).days

                        if 0 <= days_left <= days_ahead and status not in ["Approved", "Done"]:
                            upcoming_tasks.append({
                                "task": item["name"],
                                "person": person,
                                "deadline": str(item_date),
                                "status": status,
                                "group": group_title,
                                "days_left": days_left
                            })
                    except ValueError:
                        pass

        return upcoming_tasks
    def get_task_summary(self, overdue_days=3, upcoming_days=7):
        if not self.data:
            raise ValueError("Chưa có dữ liệu. Hãy gọi fetch_board_data() trước.")
        
        from datetime import datetime
        
        today = datetime.today().date()
        total_tasks = 0
        people_set = set()
        overdue_count = 0
        upcoming_count = 0
        
        for board in self.data["data"]["boards"]:
            for item in board["items_page"]["items"]:
                total_tasks += 1
                
                person = None
                date_str = None
                status = None
                
                # Lấy thông tin person, date, status
                for col in item["column_values"]:
                    if col["id"] == "person":
                        person = col["text"]
                    elif col["id"] == "date4":
                        date_str = col["text"]
                    elif col["id"] == "status":
                        status = col["text"]
                
                # Đếm số người (loại bỏ trùng lặp)
                if person:
                    people_set.add(person)
                
                # Kiểm tra overdue và upcoming tasks
                if date_str:
                    try:
                        item_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        days_diff = (today - item_date).days
                        
                        # Chỉ tính tasks chưa hoàn thành
                        if status not in ["Approved", "Done"]:
                            # Task trễ deadline
                            if days_diff > overdue_days:
                                overdue_count += 1
                            # Task sắp đến hạn (từ hôm nay đến upcoming_days ngày tới)
                            elif -upcoming_days <= days_diff <= 0:
                                upcoming_count += 1
                                
                    except ValueError:
                        # Bỏ qua nếu format ngày không đúng
                        pass
        
        return {
            "total_tasks": total_tasks,
            "total_people": len(people_set),
            "overdue_tasks": overdue_count,
            "upcoming_tasks": upcoming_count
        }