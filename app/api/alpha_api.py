from fastapi import APIRouter
from app.agents.alpha_agent.monday_agent import MondayChatbotAgent
from slack_sdk import WebClient
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt import App
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import os

agent = MondayChatbotAgent()

router = APIRouter()

slack_app = App(
    token=os.getenv("SLACK_TOKEN"), signing_secret=os.getenv("SLACK_SIGNING_SECRET")
)
handler = SlackRequestHandler(slack_app)

async def process_mention(event_data: dict, question: str) -> None:
    try:
        channel_id = event_data["event"]["channel"]
        print(f"Processing mention: '{question}' in channel {channel_id}")
        
        response = agent.process_message(message=question, thread_id=channel_id)
        print(f"Generated response: '{response}'")
        slack_client = WebClient(token=os.getenv("SLACK_TOKEN"))
        slack_client.chat_postMessage(
            channel=channel_id, 
            text=response, 
        )
        print(f"Replied to channel {channel_id} with: '{response}'")
    except Exception as e:
        print(f"Error processing slack bot mention: {e}")


@router.post("/slack/events")
async def slack_events_endpoint(req: Request, background_tasks: BackgroundTasks):
    body = await req.json()

    print(f"++++++++++++++Received Slack event: {body}")

    if body.get("type") == "url_verification":
        return JSONResponse(content={"challenge": body.get("challenge")})

    if body.get("type") == "event_callback":
        event = body.get("event", {})

        # Check for retry header
        if 'x-slack-retry-num' in req.headers:
            print(f"Detected a retry from Slack (reason: {req.headers.get('x-slack-retry-reason')}). Ignoring.")
            return JSONResponse(content={"status": "ok, retry ignored"})

        user_id = event.get("user")
        SLACK_BOT_USER_ID = os.getenv("SLACK_BOT_USER_ID")
        if user_id == SLACK_BOT_USER_ID:
            print(f"Ignoring message from self (bot user ID: {SLACK_BOT_USER_ID})")
            return JSONResponse(content={"status": "ignored self-message"})

        if event.get("type") == "app_mention":
            mention = f"<@{SLACK_BOT_USER_ID}>"
            question = event.get("text", "").replace(mention, "").strip()
            background_tasks.add_task(process_mention, body, question)

    return JSONResponse(content={"status": "ok"})