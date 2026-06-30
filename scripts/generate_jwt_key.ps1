# ==============================================================================
# Windows PowerShell용 JWT 대칭키 자동 생성 스크립트
# 실행 방법: PowerShell을 열고 프로젝트 루트 폴더에서 .\scripts\generate_jwt_key.ps1 실행
# ==============================================================================

$TargetDir = Join-Path $PSScriptRoot "../backend"
$KeyPath = Join-Path $TargetDir ".jwt_secret_key"

if (Test-Path $KeyPath) {
    Write-Host "[Info] JWT Secret Key file already exists at: $KeyPath" -ForegroundColor Yellow
    Exit 0
}

# 32바이트 URL-safe 보안 난수 생성
$Bytes = New-Object Byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($Bytes)
$GeneratedKey = [Convert]::ToBase64String($Bytes) -replace '\+','-' -replace '/','_' -replace '=',''

# 파일 쓰기
Set-Content -Path $KeyPath -Value $GeneratedKey -Encoding utf8
Write-Host "[Success] Secure JWT Secret Key file generated at: $KeyPath" -ForegroundColor Green
