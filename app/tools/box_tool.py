import os
from boxsdk import Client, OAuth2
from dotenv import load_dotenv
import pandas as pd
import io

import os
import io
import pandas as pd
from boxsdk import Client, OAuth2
from dotenv import load_dotenv
from pandasai_openai import AzureOpenAI
import pandasai as pai
from app.core.config import Config

class ToolBox:
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.developer_token = os.getenv("DEVELOPER_TOKEN")
        print(f"developer_token: {self.developer_token}")
        print(f"client_id: {self.client_id}")
        print(f"client_secret: {self.client_secret}")
        self.client = self._authenticate()
        self.llm = AzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            api_version=Config.AZURE_OPENAI_API_VERSION,
            deployment_name=Config.AZURE_OPENAI_DEPLOYMENT_NAME,
        )
        pai.config.set({"llm": self.llm})

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
        try:
            root_folder = self.client.folder(folder_id='0')
            items = root_folder.get_items()
            file_id = None

            for item in items:
                if item.name == file_name:
                    file_id = item.id
                    break

            if file_id:
                box_file = self.client.file(file_id).get()
                file_content = box_file.content()
                excel_data = io.BytesIO(file_content)
                df = pd.read_excel(excel_data)
                df.columns = df.columns.map(str)
                return df
            else:
                print(f'File {file_name} not found in Box root folder.')
        except Exception as e:
            print(f'An error occurred during Excel analysis: {e}')

    def query_dataframe(self, df, question: str):
        try:
            smart_df = pai.DataFrame(df)
            return smart_df.chat(question)
        except Exception:
            return "Tôi chưa rõ câu hỏi của bạn, vui lòng hỏi chi tiết hơn."
