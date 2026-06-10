# 💻 Getting Started (서버 실행 가이드)

프로젝트를 처음 클론(Clone) 받은 후, 프론트엔드와 백엔드 서버를 로컬 환경에서 **HTTPS**로 구동하기 위해 다음 단계들을 순서대로 수행해 주세요.

---

## 0. 로컬 SSL 인증서 발급 (`mkcert` 세팅)
웹 API 보안 정책(예: 쿠키 전송, 소셜 로그인 등)을 로컬에서 정상적으로 테스트하기 위해, 프론트엔드와 백엔드 모두 `HTTPS` 통신을 기본으로 합니다. 이를 위해 로컬 인증서를 발급받아야 합니다.

```bash
# 1. mkcert 설치 (운영체제에 맞게 선택)
# [Windows]
choco install mkcert
# [Mac]
brew install mkcert
# [Linux / Ubuntu]
sudo apt update
sudo apt install libnss3-tools mkcert

# (만약 apt에서 mkcert를 찾을 수 없는 옛날/경량 버전의 Ubuntu라면 수동 설치)
# sudo apt install libnss3-tools
# wget -O mkcert https://dl.filippo.io/mkcert/latest?for=linux/amd64
# chmod +x mkcert
# sudo mv mkcert /usr/local/bin/

# 2. 로컬 인증기관(CA) 설치
mkcert -install

# 3. 프로젝트 최상단(CodeCompass)에 인증서 폴더 생성 및 발급
mkdir certs
cd certs
mkcert localhost 127.0.0.1
```
> 위 명령어를 실행하면 `certs/` 폴더 내부에 `localhost.pem` (인증서)과 `localhost-key.pem` (개인키) 파일이 생성됩니다.

---

## 1. Backend (FastAPI) 구동 세팅
백엔드는 파이썬 가상환경(Virtual Environment) 위에서 구동합니다.

```bash
# 1. 백엔드 폴더로 이동
cd backend

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
uvicorn app.main:app --reload --ssl-keyfile ../certs/localhost-key.pem --ssl-certfile ../certs/localhost.pem
```
> 정상 실행 시 `https://localhost:8000` 으로 서버가 열립니다.

---

## 2. Frontend (React/Vite) 구동 세팅
프론트엔드는 Node.js(버전 18 이상 권장)가 설치되어 있어야 합니다.

```bash
# 1. 프론트엔드 폴더로 이동
cd frontend

# 2. 필수 라이브러리(node_modules) 설치
npm install
```

프론트엔드 서버도 발급받은 인증서를 사용하도록 `frontend/vite.config.js`를 다음과 같이 세팅합니다.

```javascript
// frontend/vite.config.js 예시
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'

export default defineConfig({
  plugins: [react()],
  server: {
    https: {
      key: fs.readFileSync('../certs/localhost-key.pem'),
      cert: fs.readFileSync('../certs/localhost.pem'),
    }
  }
})
```

```bash
# 3. Vite 개발 서버 실행
npm run dev
```
> 정상 실행 시 `https://localhost:5173` 으로 서버가 열립니다.

---

## 3. HTTPS 통신 구성 (CORS 및 API 연결)
로컬 환경에서 프론트엔드(`https://localhost:5173`)와 백엔드(`https://localhost:8000`)가 통신하기 위한 필수 설정입니다.

### 🛡️ 백엔드: CORS 설정 (main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:5173"],  # 프론트엔드의 HTTPS 주소 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 🌐 프론트엔드: Axios 환경 변수 세팅
```text
# frontend/.env
VITE_API_BASE_URL=https://localhost:8000
```
