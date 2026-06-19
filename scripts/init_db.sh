#!/bin/bash
# DB 마이그레이션 및 컨테이너 초기화 자동 실행 스크립트
echo "Initializing CodeMap database schema..."

# 1. 데이터베이스 컨테이너 구동 대기
echo "Waiting for database container to be ready..."
until docker exec postgresql-17 pg_isready -U codemap -d codemap; do
  sleep 1
done

## 2. database 디렉토리를 컨테이너 내부로 복사한 뒤 스키마 실행 (\i 상대경로 해결)
echo "Copying database SQL files to container..."
docker exec postgresql-17 mkdir -p /tmp/database
docker cp "$(dirname "$0")/../database/." postgresql-17:/tmp/database/

## 3. 스키마 적용
echo "Applying database schema init.sql..."
docker exec postgresql-17 psql -U codemap -d codemap -f /tmp/database/init.sql

## 4. 임시 파일 삭제
echo "Cleaning up temporary SQL files from container..."
docker exec postgresql-17 rm -rf /tmp/database

echo "============================================="
echo "데이터베이스 스키마 초기화가 성공적으로 완료되었습니다!"
echo "============================================="
