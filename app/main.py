
from app.api import supervisor_api
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, status
import logging
import sentry_sdk
from app.core import config

app = FastAPI(
    title="UpshotAI",
    description="AI assistant",
)

# Thêm router trực tiếp vào app
app.include_router(supervisor_api.router, tags=["Supervisor chat"])

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    logging.error(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

logging.getLogger('passlib').setLevel(logging.ERROR)

print("Running in development mode!")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)