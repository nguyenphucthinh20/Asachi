import os
from boxsdk import Client, OAuth2
from dotenv import load_dotenv
import pandas as pd
import io

class BoxAPI:
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.developer_token = os.getenv("DEVELOPER_TOKEN")
        self.client = self._authenticate()
    
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
                return df
            else:
                print(f'File {file_name} not found in Box root folder.')
        except Exception as e:
            print(f'An error occurred during Excel analysis: {e}')

box_api = BoxAPI()
