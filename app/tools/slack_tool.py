"""
Slack API integration tool
"""
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt import App
import os
from typing import Dict, Any, Optional, List
from app.tools.base_tool import BaseTool
from app.utils.exceptions import ToolException, ValidationException
from app.utils.logger import Logger
from app.utils.validators import Validator

class SlackTool(BaseTool):
    """Slack API integration tool"""
    
    def __init__(self, token: Optional[str] = None, signing_secret: Optional[str] = None, 
                 bot_user_id: Optional[str] = None):
        super().__init__("SlackTool")
        
        self.token = token or os.getenv("SLACK_TOKEN")
        self.signing_secret = signing_secret or os.getenv("SLACK_SIGNING_SECRET")
        self.bot_user_id = bot_user_id or os.getenv("SLACK_BOT_USER_ID")
        
        self.logger = Logger.get_logger(self.__class__.__name__)
        self.client = None
        self.app = None
        self.handler = None
        
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Validate Slack configuration"""
        required_configs = {
            'token': self.token,
            'signing_secret': self.signing_secret,
            'bot_user_id': self.bot_user_id
        }
        
        for config_name, config_value in required_configs.items():
            if not config_value:
                raise ValidationException(f"Slack {config_name} is required")
    
    def initialize(self) -> None:
        """Initialize the Slack client and app"""
        try:
            # Initialize WebClient
            self.client = WebClient(token=self.token)
            
            # Initialize Bolt app
            self.app = App(token=self.token, signing_secret=self.signing_secret)
            self.handler = SlackRequestHandler(self.app)
            
            # Test the connection
            auth_response = self.client.auth_test()
            
            self.logger.info(f"Slack tool initialized successfully for team: {auth_response['team']}")
            
        except SlackApiError as e:
            raise ToolException(f"Failed to initialize Slack client: {e.response['error']}")
        except Exception as e:
            raise ToolException(f"Failed to initialize Slack tool: {str(e)}")
    
    def is_healthy(self) -> bool:
        """Check if the Slack client is healthy"""
        try:
            if not self.client:
                return False
            
            response = self.client.auth_test()
            return response["ok"]
            
        except Exception as e:
            self.logger.error(f"Slack health check failed: {str(e)}")
            return False
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.client = None
        self.app = None
        self.handler = None
        self.logger.info("Slack tool cleaned up")
    
    def send_message(self, channel: str, text: str, thread_ts: Optional[str] = None, 
                    blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Send message to Slack channel"""
        try:
            self.ensure_initialized()
            Validator.validate_non_empty_string(channel, "channel")
            Validator.validate_non_empty_string(text, "text")
            
            # Sanitize message content
            sanitized_text = Validator.sanitize_user_input(text)
            
            response = self.client.chat_postMessage(
                channel=channel,
                text=sanitized_text,
                thread_ts=thread_ts,
                blocks=blocks
            )
            
            if response["ok"]:
                message_info = {
                    'channel': response['channel'],
                    'timestamp': response['ts'],
                    'message': response['message']['text']
                }
                self.logger.info(f"Message sent successfully to channel: {channel}")
                return message_info
            else:
                raise ToolException(f"Failed to send message: {response.get('error', 'Unknown error')}")
                
        except SlackApiError as e:
            self.logger.error(f"Failed to send Slack message: {e.response['error']}")
            raise ToolException(f"Failed to send Slack message: {e.response['error']}")
    
    def get_channel_info(self, channel: str) -> Dict[str, Any]:
        """Get information about a Slack channel"""
        try:
            self.ensure_initialized()
            Validator.validate_non_empty_string(channel, "channel")
            
            response = self.client.conversations_info(channel=channel)
            
            if response["ok"]:
                channel_data = response["channel"]
                channel_info = {
                    'id': channel_data['id'],
                    'name': channel_data.get('name', 'Unknown'),
                    'is_private': channel_data.get('is_private', False),
                    'member_count': channel_data.get('num_members', 0)
                }
                
                self.logger.info(f"Retrieved info for channel: {channel_info['name']}")
                return channel_info
            else:
                raise ToolException(f"Failed to get channel info: {response.get('error', 'Unknown error')}")
                
        except SlackApiError as e:
            self.logger.error(f"Failed to get channel info: {e.response['error']}")
            raise ToolException(f"Failed to get channel info: {e.response['error']}")
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about a Slack user"""
        try:
            self.ensure_initialized()
            Validator.validate_non_empty_string(user_id, "user_id")
            
            response = self.client.users_info(user=user_id)
            
            if response["ok"]:
                user_data = response["user"]
                user_info = {
                    'id': user_data['id'],
                    'name': user_data.get('name', 'Unknown'),
                    'real_name': user_data.get('real_name', 'Unknown'),
                    'email': user_data.get('profile', {}).get('email', 'Unknown'),
                    'is_bot': user_data.get('is_bot', False)
                }
                
                self.logger.info(f"Retrieved info for user: {user_info['name']}")
                return user_info
            else:
                raise ToolException(f"Failed to get user info: {response.get('error', 'Unknown error')}")
                
        except SlackApiError as e:
            self.logger.error(f"Failed to get user info: {e.response['error']}")
            raise ToolException(f"Failed to get user info: {e.response['error']}")
    
    def extract_mention_text(self, text: str) -> str:
        """Extract and clean text from Slack mention"""
        try:
            Validator.validate_non_empty_string(text, "text")
            
            mention = f"<@{self.bot_user_id}>"
            cleaned_text = text.replace(mention, "").strip()
            
            # Additional cleaning for Slack formatting
            cleaned_text = Validator.sanitize_user_input(cleaned_text)
            
            self.logger.debug(f"Extracted mention text: '{cleaned_text}' from: '{text}'")
            return cleaned_text
            
        except Exception as e:
            self.logger.error(f"Failed to extract mention text: {str(e)}")
            return text
    
    def format_message_blocks(self, title: str, content: str, 
                             color: str = "good") -> List[Dict[str, Any]]:
        """Format message as Slack blocks for rich formatting"""
        try:
            Validator.validate_non_empty_string(title, "title")
            Validator.validate_non_empty_string(content, "content")
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{title}*\n{content}"
                    }
                }
            ]
            
            return blocks
            
        except Exception as e:
            self.logger.error(f"Failed to format message blocks: {str(e)}")
            # Return simple text block as fallback
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": f"{title}\n{content}"
                    }
                }
            ]
    
    def handle_app_mention(self, event_data: Dict[str, Any], response_handler) -> None:
        """Handle app mention events"""
        try:
            if not event_data or "event" not in event_data:
                self.logger.warning("Invalid event data received")
                return
            
            event = event_data["event"]
            channel_id = event.get("channel")
            text = event.get("text", "")
            
            if not channel_id:
                self.logger.warning("No channel ID in event data")
                return
            
            # Extract clean text from mention
            clean_text = self.extract_mention_text(text)
            
            # Process the message using the provided handler
            if response_handler:
                response_handler(channel_id, clean_text)
            
            self.logger.info(f"Processed app mention in channel: {channel_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle app mention: {str(e)}")
            raise ToolException(f"Failed to handle app mention: {str(e)}")

# Global instance for backward compatibility
slack_tool = SlackTool()
