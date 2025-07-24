"""
Box.com API integration tool
"""
import os
from boxsdk import Client, OAuth2
from boxsdk.exception import BoxToolException
from dotenv import load_dotenv
import pandas as pd
import io
from typing import Optional, Dict, Any, List
from app.tools.base import BaseTool
from app.core.exceptions import ToolException, ValidationException
from app.core.logger import Logger


class BoxTool(BaseTool):
    """Box.com API integration tool"""
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, 
                 developer_token: Optional[str] = None):
        super().__init__("BoxTool")
        load_dotenv()
        
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.developer_token = developer_token or os.getenv("DEVELOPER_TOKEN")
        
        self.logger = Logger.get_logger(self.__class__.__name__)
        self.client = None
        
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Validate Box API configuration"""
        required_configs = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'developer_token': self.developer_token
        }
        
        for config_name, config_value in required_configs.items():
            if not config_value:
                raise ValidationException(f"Box API {config_name} is required")
    
    def initialize(self) -> None:
        """Initialize the Box API client"""
        try:
            auth = OAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
                access_token=self.developer_token,
            )
            self.client = Client(auth)
            
            # Test the connection
            self.get_user_info()
            self.logger.info("Box API client initialized successfully")
            
        except Exception as e:
            raise ToolException(f"Failed to initialize Box API client: {str(e)}")
    
    def is_healthy(self) -> bool:
        """Check if the Box API client is healthy"""
        try:
            if not self.client:
                return False
            
            # Simple health check by getting user info
            self.client.user(user_id='me').get(fields=['login'])
            return True
            
        except Exception as e:
            self.logger.error(f"Box API health check failed: {str(e)}")
            return False
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.client = None
        self.logger.info("Box API client cleaned up")
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information"""
        try:
            self.ensure_initialized()
            
            user = self.client.user(user_id='me').get(fields=['login', 'name'])
            user_info = {
                'email': user.login,
                'name': user.name,
                'id': user.id
            }
            
            self.logger.info(f"Retrieved user info for: {user_info['email']}")
            return user_info
            
        except BoxToolException as e:
            self.logger.error(f"Failed to get user info: {str(e)}")
            raise ToolException(f"Failed to get user info: {str(e)}")
    
    def get_folder_info(self, folder_id: str = '0') -> Dict[str, Any]:
        """Get folder information and contents"""
        try:
            self.ensure_initialized()
            
            folder = self.client.folder(folder_id=folder_id).get()
            items = folder.get_items(limit=100, offset=0)
            
            folder_info = {
                'name': folder.name,
                'owner': folder.owned_by.login if folder.owned_by else 'Unknown',
                'items': [{'name': item.name, 'type': item.type, 'id': item.id} for item in items]
            }
            
            self.logger.info(f"Retrieved info for folder: {folder_info['name']} with {len(folder_info['items'])} items")
            return folder_info
            
        except BoxToolException as e:
            self.logger.error(f"Failed to get folder info: {str(e)}")
            raise ToolException(f"Failed to get folder info: {str(e)}")
    
    def find_file_by_name(self, file_name: str, folder_id: str = '0') -> Optional[str]:
        """Find file by name in specified folder"""
        try:
            self.ensure_initialized()
            
            folder = self.client.folder(folder_id=folder_id)
            items = folder.get_items()
            
            for item in items:
                if item.name == file_name:
                    self.logger.info(f"Found file: {file_name} with ID: {item.id}")
                    return item.id
            
            self.logger.warning(f"File not found: {file_name}")
            return None
            
        except BoxToolException as e:
            self.logger.error(f"Failed to find file: {str(e)}")
            raise ToolException(f"Failed to find file: {str(e)}")
    
    def analyze_excel_file(self, file_name: str = 'metadata_ver2.xlsx', folder_id: str = '0') -> Optional[pd.DataFrame]:
        """Analyze Excel file from Box storage"""
        try:
            self.ensure_initialized()
            
            file_id = self.find_file_by_name(file_name, folder_id)
            
            if not file_id:
                self.logger.warning(f"Excel file not found: {file_name}")
                return None
            
            # Get file content
            box_file = self.client.file(file_id).get()
            file_content = box_file.content()
            excel_data = io.BytesIO(file_content)
            
            # Read Excel file
            df = pd.read_excel(excel_data)
            
            self.logger.info(f"Successfully analyzed Excel file: {file_name} with shape {df.shape}")
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to analyze Excel file: {str(e)}")
            raise ToolException(f"Failed to analyze Excel file: {str(e)}")
    
    def upload_file(self, file_path: str, file_name: Optional[str] = None, folder_id: str = '0') -> Dict[str, Any]:
        """Upload file to Box"""
        try:
            self.ensure_initialized()
            
            if not os.path.exists(file_path):
                raise ValidationException(f"File does not exist: {file_path}")
            
            upload_name = file_name or os.path.basename(file_path)
            folder = self.client.folder(folder_id=folder_id)
            
            uploaded_file = folder.upload(file_path, file_name=upload_name)
            
            file_info = {
                'id': uploaded_file.id,
                'name': uploaded_file.name,
                'size': uploaded_file.size
            }
            
            self.logger.info(f"Successfully uploaded file: {upload_name}")
            return file_info
            
        except BoxToolException as e:
            self.logger.error(f"Failed to upload file: {str(e)}")
            raise ToolException(f"Failed to upload file: {str(e)}")
    
    def download_file(self, file_id: str, download_path: str) -> bool:
        """Download file from Box"""
        try:
            self.ensure_initialized()
            
            box_file = self.client.file(file_id).get()
            file_content = box_file.content()
            
            with open(download_path, 'wb') as f:
                f.write(file_content)
            
            self.logger.info(f"Successfully downloaded file to: {download_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download file: {str(e)}")
            raise ToolException(f"Failed to download file: {str(e)}")
    
    def search_files(self, query: str, file_extensions: Optional[List[str]] = None, 
                    limit: int = 10) -> List[Dict[str, Any]]:
        """Search for files in Box"""
        try:
            self.ensure_initialized()
            
            search_results = self.client.search().query(
                query,
                limit=limit,
                offset=0,
                ancestor_folders=[self.client.folder(folder_id='0')],
                file_extensions=file_extensions or [],
            )
            
            results = []
            for item in search_results:
                item_details = item.get(fields=['name', 'size', 'modified_at'])
                results.append({
                    'id': item_details.id,
                    'name': item_details.name,
                    'size': item_details.size,
                    'modified_at': item_details.modified_at,
                    'type': item_details.type
                })
            
            self.logger.info(f"Found {len(results)} files matching query: {query}")
            return results
            
        except BoxToolException as e:
            self.logger.error(f"Failed to search files: {str(e)}")
            raise ToolException(f"Failed to search files: {str(e)}")
