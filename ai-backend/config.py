import os
from dotenv import load_dotenv

# 프로젝트 루트 기준 .env 파일 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))

# OpenAI 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# AI 서버 테스트용 포트
PORT = int(os.getenv("PORT", "5001"))

# 웹 백엔드 URL (DB 저장용 POST)
WEB_BACKEND_URL = os.getenv("WEB_BACKEND_URL", "http://127.0.0.1:5000/stores/process")