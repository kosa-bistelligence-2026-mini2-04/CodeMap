# 파이썬 3.12 슬림 버전 기반
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 빌드에 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 코드 복사
COPY . .

# FastAPI 포트 노출
EXPOSE 8000

# 컨테이너 실행 시 Uvicorn 서버 가동
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
