import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI, AsyncAzureOpenAI

# プロジェクトルート（backend/common/ から2つ上）
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"

# .envファイルの読み込み
load_dotenv(dotenv_path=ENV_PATH)

API_TYPE = os.environ.get("API_TYPE")
if API_TYPE == "HOZEN":
    AZURE_ENDPOINT = os.environ.get("HOZEN_ENDPOINT")
    AZURE_API_KEY = os.environ.get("HOZEN_API_KEY")
    AZURE_API_VERSION = os.environ.get("HOZEN__API_VERSION")


def get_openai_client() -> AzureOpenAI:
    """
    Azure OpenAI の同期クライアントを取得

    Returns:
        AzureOpenAI: 設定済みのAzure OpenAIクライアント
    """
    return AzureOpenAI(
        api_key=AZURE_API_KEY,
        azure_endpoint=AZURE_ENDPOINT,
        api_version=AZURE_API_VERSION,
    )


def get_openai_client_async() -> AsyncAzureOpenAI:
    """
    Azure OpenAI の非同期クライアントを取得

    Returns:
        AsyncAzureOpenAI: 設定済みのAzure OpenAI非同期クライアント
    """
    return AsyncAzureOpenAI(
        api_key=AZURE_API_KEY,
        azure_endpoint=AZURE_ENDPOINT,
        api_version=AZURE_API_VERSION,
    )


# デフォルトクライアント（後方互換性のため）
client = get_openai_client()
aoai_client = get_openai_client()
aoai_client_async = get_openai_client_async()
