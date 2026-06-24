# Windows Local Environment Auto-Setup Script for CodeMap
# ========================================================
# PowerShell 실행 방법:
# Set-ExecutionPolicy Bypass -Scope Process; .\scripts\setup_win.ps1

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Starting CodeMap Windows Environment Setup..." -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$rootPath = Resolve-Path "$PSScriptRoot\.."

# 1. winget 명령어 존재 여부 확인
if (-not (Get-Command "winget" -ErrorAction SilentlyContinue)) {
    Write-Host "[Error] 'winget' 패키지 관리자가 탐지되지 않았습니다." -ForegroundColor Red
    Write-Host "Windows App Installer를 업데이트하거나 수동으로 필요한 도구들을 설치하십시오." -ForegroundColor Yellow
    Exit 1
}

# 2. Python 3.12 설치 여부 확인 및 설치
if (-not (Get-Command "python" -ErrorAction SilentlyContinue) -or ((python --version) -notmatch "3\.12")) {
    Write-Host "[Info] Python 3.12 버전이 감지되지 않았습니다. winget을 통해 설치를 시작합니다..." -ForegroundColor Yellow
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    Write-Host ">> Python 3.12 설치 요청이 완료되었습니다. (반영을 위해 터미널 재시작이 필요할 수 있습니다.)" -ForegroundColor Green
} else {
    Write-Host "[Pass] Python 3.12 버전이 이미 설치되어 있습니다." -ForegroundColor Green
}

# 3. Node.js LTS 설치 여부 확인 및 설치
if (-not (Get-Command "node" -ErrorAction SilentlyContinue)) {
    Write-Host "[Info] Node.js가 감지되지 않았습니다. winget을 통해 LTS 버전 설치를 시작합니다..." -ForegroundColor Yellow
    winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
    Write-Host ">> Node.js LTS 설치 요청이 완료되었습니다." -ForegroundColor Green
} else {
    Write-Host "[Pass] Node.js가 이미 설치되어 있습니다. (버전: $(node -v))" -ForegroundColor Green
}

# 4. mkcert 설치 여부 확인 및 설치
if (-not (Get-Command "mkcert" -ErrorAction SilentlyContinue)) {
    Write-Host "[Info] mkcert가 감지되지 않았습니다. winget을 통해 설치합니다..." -ForegroundColor Yellow
    winget install FiloSottile.mkcert --silent --accept-package-agreements --accept-source-agreements
    Write-Host ">> mkcert 설치가 완료되었습니다." -ForegroundColor Green
} else {
    Write-Host "[Pass] mkcert가 이미 설치되어 있습니다." -ForegroundColor Green
}

# 환경 변수 리프레시 (winget 설치 직후 명령어 사용이 가능하도록 시도)
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 5. mkcert 로컬 CA 등록 및 SSL 인증서 자동 발급
Write-Host "[Step 1/4] Configuring SSL certificates using mkcert..." -ForegroundColor Cyan
try {
    & mkcert -install
    
    $certsDir = "$rootPath\backend\certs"
    if (-not (Test-Path $certsDir)) {
        New-Item -ItemType Directory -Path $certsDir | Out-Null
    }
    
    Push-Location $certsDir
    & mkcert localhost 127.0.0.1
    Pop-Location
    Write-Host ">> SSL 인증서가 성공적으로 발급되었습니다. (backend/certs/)" -ForegroundColor Green
} catch {
    Write-Host "[Warning] mkcert CA 등록 또는 인증서 발급 중 경고/오류가 발생했습니다: $_" -ForegroundColor Yellow
    Write-Host "나중에 터미널을 다시 열어 'mkcert -install' 및 'mkcert localhost 127.0.0.1'을 수동으로 수행해 주세요." -ForegroundColor Yellow
}

# 6. pnpm 글로벌 설치
Write-Host "[Step 2/4] Installing global pnpm..." -ForegroundColor Cyan
if (-not (Get-Command "pnpm" -ErrorAction SilentlyContinue)) {
    & npm install -g pnpm
    Write-Host ">> pnpm이 글로벌 설치되었습니다." -ForegroundColor Green
} else {
    Write-Host "[Pass] pnpm이 이미 설치되어 있습니다." -ForegroundColor Green
}

# 7. 백엔드 가상환경(venv) 구축 및 라이브러리 설치
Write-Host "[Step 3/4] Setting up Python virtual environment and dependencies..." -ForegroundColor Cyan
$backendDir = "$rootPath\backend"
$venvDir = "$backendDir\venv"

if (-not (Test-Path $venvDir)) {
    & python -m venv $venvDir
    Write-Host ">> 가상환경(venv)이 생성되었습니다." -ForegroundColor Green
}

# 가상환경의 pip를 호출하여 requirements.txt 설치 실행
Write-Host ">> 백엔드 requirements.txt 의존성을 설치 중입니다. (이 작업은 수 분이 소요될 수 있습니다.)" -ForegroundColor Yellow
& "$venvDir\Scripts\pip.exe" install --upgrade pip
& "$venvDir\Scripts\pip.exe" install -r "$backendDir\requirements.txt"
Write-Host ">> 백엔드 의존성 설치가 완료되었습니다." -ForegroundColor Green

# setup_env.py 실행을 통해 .env 템플릿 생성
& "$venvDir\Scripts\python.exe" "$backendDir\setup_env.py"

# 8. 프론트엔드 패키지 설치
Write-Host "[Step 4/4] Installing Frontend dependencies using pnpm..." -ForegroundColor Cyan
$frontendDir = "$rootPath\frontend"
Push-Location $frontendDir
& pnpm install
Pop-Location
Write-Host ">> 프론트엔드 의존성(node_modules) 설치가 완료되었습니다." -ForegroundColor Green

# 9. 완료 안내 화면 출력
Write-Host "=========================================================================" -ForegroundColor Green
Write-Host "🎉 CodeMap 로컬 개발 환경 기본 세팅이 성공적으로 완료되었습니다! 🎉" -ForegroundColor Green
Write-Host "=========================================================================" -ForegroundColor Green
Write-Host "성공적으로 구동하기 위해 아래 가이드에 따라 수동 설정을 진행해 주십시오:" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "1. [중요] Docker Desktop을 구동하고 PostgreSQL 컨테이너가 정상 기동 중인지 확인해 주세요." -ForegroundColor Yellow
Write-Host "2. 'backend/.env' 파일을 열어 아래 필수 보안 환경 변수를 기입해 주세요." -ForegroundColor Yellow
Write-Host "   - DB_PASSWORD='<로컬DB비밀번호>'" -ForegroundColor Yellow
Write-Host "   - OPENAI_API_KEY='<OpenAI API 키>'" -ForegroundColor Yellow
Write-Host "   - GITHUB_TOKEN='<GitHub PAT 토큰>' (API 호출 한계 방지용)" -ForegroundColor Yellow
Write-Host "3. [백엔드 실행] 새 PowerShell 창을 열어 아래 명령어를 실행해 주세요:" -ForegroundColor Cyan
Write-Host "   cd backend" -ForegroundColor Cyan
Write-Host "   .\\venv\\Scripts\\Activate.ps1" -ForegroundColor Cyan
Write-Host "   uvicorn app.main:app --reload --ssl-keyfile certs/localhost-key.pem --ssl-certfile certs/localhost.pem" -ForegroundColor Cyan
Write-Host "4. [프론트엔드 실행] 또 다른 PowerShell 창을 열어 아래 명령어를 실행해 주세요:" -ForegroundColor Cyan
Write-Host "   cd frontend" -ForegroundColor Cyan
Write-Host "   pnpm dev -- --experimental-https --experimental-https-key ../backend/certs/localhost-key.pem --experimental-https-cert ../backend/certs/localhost.pem" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Green
