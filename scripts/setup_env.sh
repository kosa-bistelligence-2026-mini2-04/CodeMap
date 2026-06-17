#!/bin/bash
# 로컬/운영 실행 환경(인증서, 의존성 등) 구축 셸 스크립트
echo "Setting up CodeMap local database environment..."

# 1. 기존 컨테이너 및 볼륨 상태 점검
if [ "$(docker ps -aq -f name=postgresql-17)" ]; then
    echo "Existing postgresql-17 container found. Stopping and removing it..."
    docker stop postgresql-17
    docker rm postgresql-17
fi

# 2. 볼륨 생성
docker volume create postgresql-17-volume

# 3. Docker Run 실행 (사용자 지정 스펙 적용 및 포트 포워딩 -p 5432:5432)
echo "Starting PostgreSQL 17 pgvector container..."
docker run --name postgresql-17 \
  -d \
  -p 5432:5432 \
  -e POSTGRES_USER=codemap \
  -e POSTGRES_PASSWORD=codemap \
  -e TZ=Asia/Seoul \
  -v postgresql-17-volume:/var/lib/postgresql-17/data \
  --restart always \
  pgvector/pgvector:pg17 \
  postgres -c max_connections=500

# 4. 포트포워딩 및 방화벽 설정 안내
echo "============================================="
echo "PostgreSQL pgvector가 5432 포트로 성공적으로 실행되었습니다."
echo "호스트와 컨테이너 간의 포트 포워딩(-p 5432:5432)이 완료되었습니다."
echo ""
echo "[방화벽 설정 안내 (Linux 계열 UFW 사용 시)]"
echo "외부 접속이 필요한 경우 아래 명령어를 실행하여 5432 포트를 열어주세요:"
echo "sudo ufw allow 5432/tcp"
echo "============================================="
