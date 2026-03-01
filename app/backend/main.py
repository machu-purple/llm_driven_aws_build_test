import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.common.openai_client_config import get_openai_client_async

app = FastAPI(title="チャットボット API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# フロントエンドの静的ファイル（uvicorn はプロジェクトルートで起動する想定）
ROOT_DIR = Path(os.getcwd())
FRONTEND_DIR = ROOT_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/")
async def index():
    """フロントエンドのHTMLを返す"""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """ユーザーのメッセージをLLMに送り、返答を返す"""
    message = (request.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    deployment = os.environ.get("HOZEN_DEPLOYMENT_NAME", "gpt-4o-mini")
    client = get_openai_client_async()

    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "あなたは親切なアシスタントです。簡潔に答えてください。"},
                {"role": "user", "content": message},
            ],
            temperature=0.7,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {str(e)}")

    content = response.choices[0].message.content if response.choices else ""
    return ChatResponse(reply=content or "(返答がありません)")
