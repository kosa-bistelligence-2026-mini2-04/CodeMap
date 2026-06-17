# 💻 Getting Started (서버 실행 가이드)

프로젝트를 처음 클론(Clone) 받은 후, 프론트엔드와 백엔드 서버를 로컬 환경에서 구동하기 위해 다음 단계들을 순서대로 수행해 주세요.

---

## 0. 로컬 SSL 인증서 발급 (`mkcert` 세팅)
웹 API 보안 정책(예: 쿠키 전송, 소셜 로그인 등)을 로컬에서 정상적으로 테스트하기 위해, 백엔드는 `HTTPS` 통신을 기본으로 합니다. 이를 위해 로컬 인증서를 발급받아야 합니다.

```bash
# 1. mkcert 설치 (운영체제에 맞게 선택)
# [Windows]
choco install mkcert
# [Mac]
brew install mkcert
# [Linux / Ubuntu]
sudo apt update
sudo apt install libnss3-tools mkcert

# 2. 로컬 인증기관(CA) 설치
mkcert -install

# 3. 백엔드 폴더 내에 인증서 폴더 생성 및 발급
mkdir -p apps/backend/certs
cd apps/backend/certs
mkcert localhost 127.0.0.1
```
> 위 명령어를 실행하면 `apps/backend/certs/` 폴더 내부에 `localhost.pem` (인증서)과 `localhost-key.pem` (개인키) 파일이 생성됩니다.

---

## 1. Backend (FastAPI) 구동 세팅
백엔드는 파이썬 3.12 가상환경(Virtual Environment) 위에서 구동합니다.

```bash
# 1. 백엔드 폴더로 이동
cd apps/backend

# 2. 파이썬 가상환경 생성 (최초 1회만 실행)
python -m venv venv

# 3. 가상환경 활성화
# - Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# - Mac/Linux:
source venv/bin/activate

# 4. 필수 라이브러리 설치
pip install -r requirements.txt

# 5. FastAPI 서버 실행 (HTTPS 적용)
uvicorn app.main:app --reload --ssl-keyfile certs/localhost-key.pem --ssl-certfile certs/localhost.pem --port 8000
```
> 정상 실행 시 `https://localhost:8000` 으로 서버가 열립니다.

---

## 2. Frontend (React/Next.js) 구동 세팅
프론트엔드는 Node.js(버전 18 이상 권장) 및 Next.js 16 (React 19)이 사용됩니다.

```bash
# 1. 프론트엔드 폴더로 이동
cd apps/frontend

# 2. 필수 라이브러리(node_modules) 설치
npm install

# 3. Next.js 개발 서버 실행
npm run dev
```
> 정상 실행 시 `http://localhost:3000` 으로 개발 서버가 열립니다.

---

## 3. 통신 구성 (CORS 및 API 연결)
로컬 개발 환경에서 프론트엔드(`http://localhost:3000`)와 백엔드(`https://localhost:8000`)가 통신하기 위한 필수 설정입니다.

### 🛡️ 백엔드: CORS 설정 (main.py)
백엔드 FastAPI의 CORS Origin 설정에는 프론트엔드가 구동되는 로컬 주소(`http://localhost:3000` 및 `https://localhost:3000`)를 허용해주어야 브라우저 쿠키 및 크레덴셜 통신이 정상화됩니다.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:3000"],  # 프론트엔드 주소 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 🌐 프론트엔드: 백엔드 API 서버 URL 세팅
Next.js는 `next.config.ts` 파일 내에 API 요청 프록시(Rewrites) 설정이 내장되어 있습니다. 브라우저에서 `/api/:path*`로 보내는 모든 요청은 Next.js 서버를 통해 백엔드 서버로 자동 중계됩니다.

이를 활성화하기 위해 환경 변수 `BACKEND_URL`을 설정합니다.

```text
# apps/frontend/.env.local (혹은 .env)
BACKEND_URL=https://localhost:8000
```
