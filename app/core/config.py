import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN")
    MONDAY_API_URL = os.getenv("MONDAY_API_URL")
    MONDAY_BOARD_IDS = os.getenv("MONDAY_BOARD_IDS", "").split(",") if os.getenv("MONDAY_BOARD_IDS") else []

    SLACK_TOKEN = os.getenv("SLACK_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_BOT_USER_ID = os.getenv("SLACK_BOT_USER_ID")

    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    BOX_CLIENT_ID = os.getenv("BOX_CLIENT_ID", "jy1i3o8gsfoiibxz0q110vq1o1e8se96")
    BOX_CLIENT_SECRET = os.getenv("BOX_CLIENT_SECRET", "PdNVYlNa518gdqr5Mn6MJf9qXMDVfW8X")
    BOX_REDIRECT_URI = os.getenv("BOX_REDIRECT_URI", "http://localhost:8000/callback")
    BOX_DEVELOPER_TOKEN = os.getenv("BOX_DEVELOPER_TOKEN", "LtGzfUQhCWO636EvcNfppzMaGCFuCBJ5")

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "azure_openai")
    
    DEFAULT_MAX_TOKENS = 400
    DEFAULT_TEMPERATURE = 0.7
