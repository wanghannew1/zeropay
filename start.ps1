# ZeroPay 个人工资发放查询 - Windows 一键启动脚本
# 参考 approval_feishu/start.ps1 模式：uv pip 安装依赖并启动，无需手动激活虚拟环境。
# 建议通过 start.bat 双击启动；直接运行本文件需在 PowerShell 中执行: .\start.ps1

Set-Location $PSScriptRoot

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ZeroPay 个人工资发放查询" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Check .env ---
if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] 未找到 .env 配置文件" -ForegroundColor Red
    Write-Host "请复制模板并填入数据库口令:" -ForegroundColor Yellow
    Write-Host "  copy .env.example .env" -ForegroundColor Yellow
    Write-Host "  然后编辑 .env，将 DB_PASSWORD=<数据库口令> 替换为真实口令" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

if (Select-String -Path ".env" -Pattern "^DB_PASSWORD=<" -Quiet) {
    Write-Host "[WARN] .env 中 DB_PASSWORD 仍为占位符，请先填入真实数据库口令" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

# --- 2. Locate Python (uv 虚拟环境优先) ---
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Write-Host "[venv] 创建 uv 虚拟环境..." -ForegroundColor Green
        & uv venv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] uv venv 创建失败" -ForegroundColor Red
            Read-Host "按回车键退出"
            exit 1
        }
    }
    $_py = ".venv\Scripts\python.exe"
    Write-Host "[venv] 使用 uv 虚拟环境: .venv" -ForegroundColor Green
}
elseif (Test-Path ".venv\Scripts\python.exe") {
    $_py = ".venv\Scripts\python.exe"
    Write-Host "[venv] 发现虚拟环境: .venv" -ForegroundColor Green
}
elseif (Test-Path "venv\Scripts\python.exe") {
    $_py = "venv\Scripts\python.exe"
    Write-Host "[venv] 发现虚拟环境: venv" -ForegroundColor Green
}
else {
    python --version 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $_py = "python"
        Write-Host "[python] 使用系统 Python（未找到 uv 与虚拟环境）" -ForegroundColor Yellow
        Write-Host "         建议安装 uv 自动管理虚拟环境: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor DarkGray
    }
    else {
        Write-Host "[ERROR] 未在 PATH 中找到 Python 或 uv" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}

# --- 3. Pick installer (uv pip first, then python -m pip) ---
if ($uv) {
    $_install = "uv pip install -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple"
    Write-Host "[deps] 使用 uv pip (清华镜像)" -ForegroundColor Green
}
else {
    & $_py -m pip --version 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] uv 与 pip 均不可用" -ForegroundColor Red
        Write-Host "安装 uv: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Yellow
        Read-Host "按回车键退出"
        exit 1
    }
    $_install = "$_py -m pip install -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple"
    Write-Host "[deps] 使用 pip (清华镜像)" -ForegroundColor Green
}

# --- 4. Install dependencies (import 检查，缺失才安装) ---
Write-Host "[deps] 检查依赖..." -ForegroundColor Green
& $_py -c "import flask, oracledb, openpyxl, dotenv" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[deps] 安装中..." -ForegroundColor Yellow
    Invoke-Expression $_install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] 依赖安装失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}
Write-Host "[deps] 就绪" -ForegroundColor Green

# --- 5. Oracle Instant Client (Oracle 11g 必须 thick 模式) ---
if (-not $env:ORACLE_CLIENT_LIB_DIR) {
    $candidates = @(
        "C:\oracle\instantclient_23_4",
        "C:\instantclient_23_4",
        "$PSScriptRoot\instantclient_23_4"
    )
    foreach ($c in $candidates) {
        if (Test-Path "$c\oci.dll") {
            $env:ORACLE_CLIENT_LIB_DIR = $c
            break
        }
    }
}

if ($env:ORACLE_CLIENT_LIB_DIR -and (Test-Path "$($env:ORACLE_CLIENT_LIB_DIR)\oci.dll")) {
    $env:PATH = "$($env:ORACLE_CLIENT_LIB_DIR);" + $env:PATH
    Write-Host "[oracle] Instant Client: $($env:ORACLE_CLIENT_LIB_DIR)" -ForegroundColor Green
}
else {
    Write-Host "[oracle] 未找到 Oracle Instant Client (oci.dll)，启动可能报 DPI-1047" -ForegroundColor Yellow
    Write-Host "         请安装 Instant Client 23.4 for Windows 并设置环境变量:" -ForegroundColor Yellow
    Write-Host "         setx ORACLE_CLIENT_LIB_DIR ""C:\oracle\instantclient_23_4""" -ForegroundColor Yellow
}

# --- 6. Launch ---
Write-Host ""
Write-Host "启动服务..." -ForegroundColor Green
Write-Host "浏览器访问: http://localhost:5001  |  Ctrl+C 停止" -ForegroundColor Cyan
Write-Host ""

& $_py app.py

Write-Host ""
Write-Host "服务已停止。" -ForegroundColor Yellow
Read-Host "按回车键退出"
