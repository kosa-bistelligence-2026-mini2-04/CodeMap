#!/bin/bash
# ==============================================================================
# Linux / macOS용 JWT 대칭키 자동 생성 스크립트
# 실행 방법: 프로젝트 루트 폴더에서 chmod +x scripts/generate_jwt_key.sh && ./scripts/generate_jwt_key.sh 실행
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEY_PATH="${SCRIPT_DIR}/../backend/.jwt_secret_key"

if [ -f "$KEY_PATH" ]; then
    echo -e "\033[1;33m[Info] JWT Secret Key file already exists at: ${KEY_PATH}\033[0m"
    exit 0
fi

# 32바이트 URL-safe 보안 난수 생성 (openssl 사용)
GENERATED_KEY=$(openssl rand -base64 32 | tr -d '\n' | tr '+/' '-_' | tr -d '=')

# 파일 쓰기
echo -n "$GENERATED_KEY" > "$KEY_PATH"

# 소유자 전용 권한 부여 (chmod 600)
chmod 600 "$KEY_PATH"

echo -e "\033[1;32m[Success] Secure JWT Secret Key file generated at: ${KEY_PATH}\033[0m"
