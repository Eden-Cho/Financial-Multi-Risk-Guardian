# ==============================================================================
# [Docker Multi-Stage / Production Image]
# - 서비스: Financial Multi-Risk Guardian - Backend (FastAPI)
# ==============================================================================

FROM python:3.11-slim

# 시스템 라이브러리 및 패키지 설치 (빌드 도구 및 curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 캐시 효율화를 위해 requirements.txt 복사 후 선설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 전체 소스 코드 복사
COPY . .

# SQLite DB 및 마스터 데이터 저장 디렉토리 보장
RUN mkdir -p data

EXPOSE 8000

# Gunicorn / Uvicorn 기반 프로덕션 구동
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]