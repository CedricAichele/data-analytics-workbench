@echo off
setlocal

set "REPO_DIR=%~dp0"
cd /d "%REPO_DIR%" || (
    echo Could not change to repository folder:
    echo %REPO_DIR%
    pause
    exit /b 1
)

echo Data Analytics Workbench
echo Repository: %CD%
echo.

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

if exist "%VENV_PYTHON%" (
    set "APP_PYTHON=%VENV_PYTHON%"
    goto install_requirements
)

echo Local virtual environment not found. Creating .venv...

where py >nul 2>nul
if not errorlevel 1 (
    py -3 --version >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
        goto check_venv
    )
)

where python >nul 2>nul
if not errorlevel 1 (
    python --version >nul 2>nul
    if not errorlevel 1 (
        python -m venv .venv
        goto check_venv
    )
)

echo.
echo Python was not found.
echo Install Python 3.12 or newer from https://www.python.org/downloads/
echo If Windows opens Microsoft Store, disable App Execution Aliases for python.exe and python3.exe.
echo Settings ^> Apps ^> Advanced app settings ^> App execution aliases
pause
exit /b 1

:check_venv
if not exist "%VENV_PYTHON%" (
    echo.
    echo Failed to create .venv.
    echo Check that Python is installed and that venv is available.
    pause
    exit /b 1
)
set "APP_PYTHON=%VENV_PYTHON%"

:install_requirements
echo Installing or updating requirements...
"%APP_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo Starting Streamlit...
echo Open: http://127.0.0.1:8501
echo Press Ctrl+C in this window to stop the app.
echo.

"%APP_PYTHON%" -m streamlit run app/main.py --server.address 127.0.0.1 --server.port 8501
if errorlevel 1 (
    echo.
    echo Streamlit exited with an error.
    pause
    exit /b 1
)

endlocal

