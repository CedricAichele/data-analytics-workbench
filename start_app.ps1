$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "Data Analytics Workbench"
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
    if (-not (Test-Path $VenvPython)) {
        Write-Host "Local virtual environment not found. Creating .venv..."
        $exitCode = Invoke-BasePython -Arguments @("-m", "venv", ".venv")
        if ($exitCode -ne 0 -or -not (Test-Path $VenvPython)) {
            throw "Failed to create .venv."
        }
    }

    Write-Host "Installing or updating requirements..."
    & $VenvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }

    Write-Host ""
    Write-Host "Starting Streamlit..."
    Write-Host "Open: http://127.0.0.1:8501"
    Write-Host "Press Ctrl+C in this window to stop the app."
    Write-Host ""

    & $VenvPython -m streamlit run app/main.py --server.address 127.0.0.1 --server.port 8501
}
catch {
    Write-Host ""
    Write-Host "Could not start the app." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "If Python is missing, install Python 3.12 or newer from https://www.python.org/downloads/"
    Write-Host "If Windows opens Microsoft Store, disable App Execution Aliases for python.exe and python3.exe."
    Write-Host "Settings > Apps > Advanced app settings > App execution aliases"
    Read-Host "Press Enter to close"
    exit 1
}

