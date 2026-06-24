#!/bin/bash
# macOS Local Environment Auto-Setup Script for CodeMap
# =====================================================
# 실행 방법:
# chmod +x scripts/setup_mac.sh && ./scripts/setup_mac.sh

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=============================================${NC}"
echo -e "${CYAN}Starting CodeMap macOS Environment Setup...  ${NC}"
echo -e "${CYAN}=============================================${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# 1. Homebrew 설치 여부 확인
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}[Info] Homebrew가 감지되지 않았습니다. 설치를 유도합니다...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Apple Silicon 패스 연동 지원
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -f /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
else
    echo -e "${GREEN}[Pass] Homebrew가 이미 설치되어 있습니다.${NC}"
fi

# 2. Python 3.12 설치 여부 확인 및 설치
if ! command -v python3 &> /dev/null || ! python3 --version | grep -q "3.12"; then
    echo -e "${YELLOW}[Info] Python 3.12 버전이 감지되지 않았습니다. Homebrew를 통해 설치를 시작합니다...${NC}"
    brew install python@3.12
else
    echo -e "${GREEN}[Pass] Python이 설치되어 있습니다. ($(python3 --version))${NC}"
fi

# 3. Node.js 설치 여부 확인
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}[Info] Node.js가 감지되지 않았습니다. Homebrew를 통해 설치를 시작합니다...${NC}"
    brew install node
else
    echo -e "${GREEN}[Pass] Node.js가 이미 설치되어 있습니다. (버전: $(node -v))${NC}"
fi

# 4. mkcert 설치 여부 확인
if ! command -v mkcert &> /dev/null; then
    echo -e "${YELLOW}[Info] mkcert가 감지되지 않았습니다. Homebrew를 통해 설치합니다...${NC}"
    brew install mkcert
    brew install nss # 파이어폭스 등 SSL 신뢰 처리를 위함
else
    echo -e "${GREEN}[Pass] mkcert가 이미 설치되어 있습니다.${NC}"
fi

# 5. mkcert 로컬 CA 등록 및 SSL 인증서 자동 발급
echo -e "${CYAN}[Step 1/4] Configuring SSL certificates using mkcert...${NC}"
mkcert -install

CERTS_DIR="$ROOT_DIR/backend/certs"
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"
mkcert localhost 127.0.0.1
echo -e "${GREEN}>> SSL 인증서가 성공적으로 발급되었습니다. (backend/certs/)${NC}"

# 6. pnpm 글로벌 설치
echo -e "${CYAN}[Step 2/4] Installing global pnpm...${NC}"
if ! command -v pnpm &> /dev/null; then
    brew install pnpm || npm install -g pnpm
    echo -e "${GREEN}>> pnpm 설치가 완료되었습니다.${NC}"
else
    echo -e "${GREEN}[Pass] pnpm이 이미 설치되어 있습니다.${NC}"
fi

# 7. 백엔드 가상환경(venv) 구축 및 라이브러리 설치
echo -e "${CYAN}[Step 3/4] Setting up Python virtual environment and dependencies...${NC}"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    # python3.12를 명시적으로 찾거나 기본 python3 사용
    PYTHON_CMD="python3"
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
    fi
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo -e "${GREEN}>> 가상환경(venv)이 생성되었습니다.${NC}"
fi

echo -e "${YELLOW}>> 백엔드 의존성을 설치 중입니다. (이 작업은 수 분이 소요될 수 있습니다.)${NC}"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
echo -e "${GREEN}>> 백엔드 의존성 설치가 완료되었습니다.${NC}"

# setup_env.py 실행을 통해 .env 템플릿 생성
"$VENV_DIR/bin/python" "$BACKEND_DIR/setup_env.py"

# 8. 프론트엔드 패키지 설치
echo -e "${CYAN}[Step 4/4] Installing Frontend dependencies using pnpm...${NC}"
cd "$ROOT_DIR/frontend"
pnpm install
echo -e "${GREEN}>> 프론트엔드 의존성 설치가 완료되었습니다.${NC}"

# 9. 완료 안내 화면 출력
echo -e "${GREEN}=========================================================================${NC}"
echo -e "${GREEN}🎉 CodeMap 로컬 개발 환경 기본 세팅이 성공적으로 완료되었습니다! 🎉${NC}"
echo -e "${GREEN}=========================================================================${NC}"
echo -e "성공적으로 구동하기 위해 아래 가이드에 따라 수동 설정을 진행해 주십시오:"
echo ""
echo -e "${YELLOW}1. [중요] Docker Desktop을 구동하고 PostgreSQL 컨테이너가 정상 기동 중인지 확인해 주세요.${NC}"
echo -e "${YELLOW}2. 'backend/.env' 파일을 열어 아래 필수 보안 환경 변수를 기입해 주세요.${NC}"
echo -e "${YELLOW}   - DB_PASSWORD='<로컬DB비밀번호>'${NC}"
echo -e "${YELLOW}   - OPENAI_API_KEY='<OpenAI API 키>'${NC}"
echo -e "${YELLOW}   - GITHUB_TOKEN='<GitHub PAT 토큰>' (API 호출 한계 방지용)${NC}"
echo -e "${CYAN}3. [백엔드 실행] 새 터미널 창을 열어 아래 명령어를 실행해 주세요:${NC}"
echo -e "${CYAN}   cd backend${NC}"
echo -e "${CYAN}   source venv/bin/activate${NC}"
echo -e "${CYAN}   uvicorn app.main:app --reload --ssl-keyfile certs/localhost-key.pem --ssl-certfile certs/localhost.pem${NC}"
echo -e "${CYAN}4. [프론트엔드 실행] 또 다른 터미널 창을 열어 아래 명령어를 실행해 주세요:${NC}"
echo -e "${CYAN}   cd frontend${NC}"
echo -e "${CYAN}   pnpm dev -- --experimental-https --experimental-https-key ../backend/certs/localhost-key.pem --experimental-https-cert ../backend/certs/localhost.pem${NC}"
echo -e "${GREEN}=========================================================================${NC}"
