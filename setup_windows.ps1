$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "Data Analytics Workbench Windows Setup"
Write-Host "Repository: $RepoRoot"
Write-Host ""

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

function Test-PythonCommand {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    try {
        $null = & $Command @Arguments --version 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Invoke-BasePython {
    param([string[]]$Arguments)

    if (Test-PythonCommand -Command "py" -Arguments @("-3")) {
        & py -3 @Arguments
        return $LASTEXITCODE
    }

    if (Test-PythonCommand -Command "python" -Arguments @()) {
        & python @Arguments
        return $LASTEXITCODE
    }

    throw "Python was not found. Install Python 3.12 or newer, or enable the py launcher."
}

try {
    Write-Host "Checking Python..."
    $null = Invoke-BasePython -Arguments @("--version")

    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creating .venv..."
        $exitCode = Invoke-BasePython -Arguments @("-m", "venv", ".venv")
        if ($exitCode -ne 0 -or -not (Test-Path $VenvPython)) {
            throw "Failed to create .venv."
        }
    }
    else {
        Write-Host ".venv already exists."
    }

    Write-Host "Installing dependencies..."
    & $VenvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }

    if (Test-Path "requirements-dev.txt") {
        Write-Host "Installing development dependencies..."
        & $VenvPython -m pip install -r requirements-dev.txt
        if ($LASTEXITCODE -ne 0) {
            throw "Development dependency installation failed."
        }
    }

    Write-Host "Compiling app..."
    & $VenvPython -m compileall app
    if ($LASTEXITCODE -ne 0) {
        throw "compileall failed."
    }

    Write-Host "Running tests..."
    & $VenvPython -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw "pytest failed."
    }

    Write-Host ""
    Write-Host "Setup complete." -ForegroundColor Green
    Write-Host "Start the app with:"
    Write-Host "  .\start_app.ps1"
    Write-Host "or double-click:"
    Write-Host "  start_app.bat"
    Write-Host ""
    Write-Host "URL: http://127.0.0.1:8501"
}
catch {
    Write-Host ""
    Write-Host "Setup failed." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Python 3.12 or newer from https://www.python.org/downloads/"
    Write-Host "If Windows opens Microsoft Store, disable App Execution Aliases for python.exe and python3.exe."
    Write-Host "Settings > Apps > Advanced app settings > App execution aliases"
    exit 1
}
