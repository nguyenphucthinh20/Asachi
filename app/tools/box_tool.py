import os
from boxsdk import Client, OAuth2
from dotenv import load_dotenv
import pandas as pd
import io
from pandasai_openai import AzureOpenAI
import pandasai as pai
from app.core.config import Config
class ToolBox:
    def __init__(self):
        load_dotenv()
        self.client_id = "ecs5dull9x2f28kh8j3b3f7cyam7v2un"
        self.client_secret = "s7lhQGVM29TRKyd4KginagPFHnsUCnR2"
        self.developer_token = "tiWbV6QysU1keagdFUPt4v6vGLL887qQ"
        self.client = self._authenticate()
        self.llm = AzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            api_version=Config.AZURE_OPENAI_API_VERSION,
            deployment_name=Config.AZURE_OPENAI_DEPLOYMENT_NAME,
        )
               
    def _authenticate(self):
        if not self.developer_token:
            raise ValueError("DEVELOPER_TOKEN must be set in environment variables.")
        
        auth = OAuth2(
            client_id=self.client_id,
            client_secret=self.client_secret,
            access_token=self.developer_token,
        )
        return Client(auth)
    
    def get_user_info(self):
        me = self.client.user(user_id='me').get(fields=['login'])
        print(f'The email of the user is: {me["login"]}')
    
    def get_folder_info(self):
        root_folder = self.client.folder(folder_id='0').get()
        print(f'The root folder is owned by: {root_folder.owned_by["login"]}')
        
        items = root_folder.get_items(limit=100, offset=0)
        print('This is the first 100 items in the root folder:')
        for item in items:
            print("   " + item.name)
    
    def analyze_excel(self, file_name='metadata_ver2.xlsx'):
        root_folder = self.client.folder(folder_id='0')
        items = root_folder.get_items()
        file_id = None
        
        for item in items:
            if item.name == file_name:
                print(f'Found file: {item.name} with ID: {item.id}')
                file_id = item.id
                break
        
        if file_id:
            # ✅ Sử dụng file_id thực tế thay vì ID cố định
            box_file = self.client.file(file_id).get()
            print(f'Analyzing file: {box_file.name}')
            file_content = box_file.content()
            excel_data = io.BytesIO(file_content)
            df = pd.read_excel(excel_data)
            return df
        else:
            print(f'File {file_name} not found in Box root folder.')
            return None
    def query_dataframe(self, df, question: str):
        try:
            # Ensure all column names are strings before passing to pandasai
            df_copy = df.copy()
            df_copy.columns = df_copy.columns.astype(str)
            
            pai.config.set({"llm": self.llm}) 
            smart_df = pai.DataFrame(df_copy)
            return smart_df.chat(question)
        except Exception as e:
            print(f"Error in query_dataframe: {e}")
            return "Tôi chưa rõ câu hỏi của bạn, vui lòng hỏi chi tiết hơn."
# Sử dụng
box_api = ToolBox()