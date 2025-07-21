import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN")
    MONDAY_API_URL = os.getenv("MONDAY_API_URL")
    MONDAY_BOARD_IDS = os.getenv("MONDAY_BOARD_IDS", "").split(",") if os.getenv("MONDAY_BOARD_IDS") else []

    SLACK_TOKEN=os.getenv("SLACK_TOKEN")
    SLACK_SIGNING_SECRET=os.getenv("SLACK_SIGNING_SECRET")
    SLACK_BOT_USER_ID=os.getenv("SLACK_BOT_USER_ID")

    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")