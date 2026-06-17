#!/bin/bash
# DB 마이그레이션 및 컨테이너 초기화 자동 실행 스크립트
echo "Initializing CodeMap database schema..."

# 1. 데이터베이스 컨테이너 구동 대기
echo "Waiting for database container to be ready..."
until docker exec postgresql-17 pg_isready -U codemap -d codemap; do
  sleep 1
done

# 2. init.sql 스크립트를 컨테이너에 스트리밍하여 실행
echo "Applying database schema init.sql..."
docker exec -i postgresql-17 psql -U codemap -d codemap < "$(dirname "$0")/../database/init.sql"

echo "============================================="
echo "데이터베이스 스키마 초기화가 성공적으로 완료되었습니다!"
echo "============================================="
