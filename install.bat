@echo off
title Milo Discord Fun Bot Installer v1.3.0

setlocal enabledelayedexpansion

:: ---------------- ASCII LOGO ----------------
echo  __  __ _ _       _         ____        _
echo ^|  \/  ^| (_) ^|_ ^|___^| ^|__     ^| ^| __ )  ___ ^| ^|_^
echo ^| ^|\/^| ^| ^| __/^|__ ^| '_ ^\____^| ^| _ ^\ / _ ^| ^| __^|
echo ^| ^|  ^| ^| ^| ^|^| (__^| ^| ^| ^|____^| ^|_) ^| (_) ^| ^| ^|_ 
echo ^|_|  |_|_| \__\___|_| |_|    |____/ \___/ \__|
echo          Milo Discord Fun Bot Installer
echo --------------------------------------------------

:: ---------------- Variables ----------------
set "REPO_URL=https://github.com/msgaxzzz/Milo-discord-fun-bot.git"
set "ZIP_URL=https://github.com/msgaxzzz/Milo-discord-fun-bot/archive/refs/heads/main.zip"
set "DIR_NAME=Milo-discord-fun-bot"
set "VENV_DIR=.venv"

if exist "main.py" if exist "requirements.txt" goto use_current_dir

if not exist "%DIR_NAME%" (
    where git >nul 2>&1
    if errorlevel 1 (
        echo Git is not available. Downloading source archive instead...
        call :download_zip_source
        if errorlevel 1 (
            pause
            exit /b 1
        )
    ) else (
        echo Cloning repository from %REPO_URL%...
        git clone "%REPO_URL%"
        if errorlevel 1 (
            echo Failed to clone repository.
            pause
            exit /b 1
        )
    )
    cd "%DIR_NAME%" || (
        echo Cannot enter directory %DIR_NAME%.
        pause
        exit /b 1
    )
) else (
    echo Directory %DIR_NAME% already exists, using it.
    cd "%DIR_NAME%" || (
        echo Cannot enter directory %DIR_NAME%.
        pause
        exit /b 1
    )
)
goto after_dir_setup

:use_current_dir
echo Installer is running inside an existing Milo checkout.

:after_dir_setup

:: Find Python 3.9+
set PYTHON_BIN=
for %%P in (python3.13 python3.12 python3.11 python3.10 python3.9 python) do (
    for /f "tokens=2 delims= " %%V in ('%%P --version 2^>^&1') do (
        set "VER=%%V"
        for /f "tokens=1,2 delims=." %%A in ("!VER!") do (
            set "MAJOR=%%A"
            set "MINOR=%%B"
            if !MAJOR! GEQ 3 (
                if !MINOR! GEQ 9 (
                    set PYTHON_BIN=%%P
                    goto foundpython
                )
            )
        )
    )
)

:foundpython
if not defined PYTHON_BIN (
    echo No compatible Python (>=3.9) found. Please install Python 3.9 or higher.
    pause
    exit /b 1
)
echo Found Python: %PYTHON_BIN%

:: Create virtual environment
if not exist "%VENV_DIR%" (
    echo Creating virtual environment in %CD%\%VENV_DIR%...
    %PYTHON_BIN% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create virtual environment. Install the Python venv component and retry.
        pause
        exit /b 1
    )
)

:: Install requirements
echo Installing dependencies from requirements.txt...
"%CD%\%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
"%CD%\%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements.txt

:: Create database directory
if not exist database (
    mkdir database
)

:: Remove existing config.json
if exist config.json del config.json

echo Configuration wizard:

:input_discord
set /p DISCORD_TOKEN=Enter Discord Bot Token (required): 
if "%DISCORD_TOKEN%"=="" (
    echo Discord Token cannot be empty.
    goto input_discord
)

set /p OPENAI_KEY=Enter OpenAI API Key (optional): 

if not "%OPENAI_KEY%"=="" (
    set /p OPENAI_API_BASE=Enter OpenAI API Base URL (default https://api.openai.com/v1): 
    if "%OPENAI_API_BASE%"=="" set OPENAI_API_BASE=https://api.openai.com/v1

    set /p ALLOW_USER_KEYS=Allow user-provided OpenAI Keys? (true/false, default true): 
    if /i not "%ALLOW_USER_KEYS%"=="true" if /i not "%ALLOW_USER_KEYS%"=="false" set ALLOW_USER_KEYS=true

    set /p DEFAULT_CHAT_MODEL=Enter default chat model (default gpt-4o-mini): 
    if "%DEFAULT_CHAT_MODEL%"=="" set DEFAULT_CHAT_MODEL=gpt-4o-mini

    set /p ALLOWED_CHAT_MODELS_INPUT=Enter allowed chat models, comma separated (default gpt-4o-mini,gpt-4o): 
    if "%ALLOWED_CHAT_MODELS_INPUT%"=="" (
        set ALLOWED_CHAT_MODELS=["gpt-4o-mini", "gpt-4o"]
    ) else (
        setlocal enabledelayedexpansion
        set "models=!ALLOWED_CHAT_MODELS_INPUT:,="",""!"
        set ALLOWED_CHAT_MODELS=[""!models!""]
        endlocal & set ALLOWED_CHAT_MODELS=%ALLOWED_CHAT_MODELS%
    )
) else (
    set OPENAI_API_BASE=
    set ALLOW_USER_KEYS=false
    set DEFAULT_CHAT_MODEL=
    set ALLOWED_CHAT_MODELS=[]
)

set /p GOOGLE_API_KEY=Enter Google API Key (optional): 
set /p GOOGLE_CSE_ID=Enter Google CSE ID (optional): 

(
echo {
echo   "DISCORD_TOKEN": "%DISCORD_TOKEN%",
echo   "OPENAI_API_KEY": "%OPENAI_KEY%",
echo   "OPENAI_API_BASE": "%OPENAI_API_BASE%",
echo   "ALLOW_USER_KEYS": %ALLOW_USER_KEYS%,
echo   "DEFAULT_CHAT_MODEL": "%DEFAULT_CHAT_MODEL%",
echo   "ALLOWED_CHAT_MODELS": %ALLOWED_CHAT_MODELS%,
echo   "GOOGLE_API_KEY": "%GOOGLE_API_KEY%",
echo   "GOOGLE_CSE_ID": "%GOOGLE_CSE_ID%"
echo }
) > config.json

echo config.json created successfully.
echo Milo Bot installation completed!
echo Please verify config.json and run:
echo   %CD%\%VENV_DIR%\Scripts\python.exe main.py
echo Or activate the virtual environment first:
echo   %VENV_DIR%\Scripts\activate
echo Update log: https://github.com/msgaxzzz/Milo-discord-fun-bot/blob/main/CHANGELOG.md

pause
exit /b 0

:download_zip_source
set "ARCHIVE_FILE=%TEMP%\milo-discord-fun-bot-main.zip"
set "ARCHIVE_ROOT=%TEMP%\milo-discord-fun-bot-install-%RANDOM%%RANDOM%"

echo Downloading %ZIP_URL%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%ZIP_URL%' -OutFile '%ARCHIVE_FILE%'"
if errorlevel 1 (
    echo Failed to download the source archive.
    exit /b 1
)

echo Extracting archive...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ARCHIVE_FILE%' -DestinationPath '%ARCHIVE_ROOT%' -Force"
if errorlevel 1 (
    echo Failed to extract the source archive.
    if exist "%ARCHIVE_FILE%" del /q "%ARCHIVE_FILE%" >nul 2>&1
    exit /b 1
)

if not exist "%ARCHIVE_ROOT%\%DIR_NAME%-main" (
    echo The extracted archive did not contain the expected folder structure.
    if exist "%ARCHIVE_FILE%" del /q "%ARCHIVE_FILE%" >nul 2>&1
    if exist "%ARCHIVE_ROOT%" rmdir /s /q "%ARCHIVE_ROOT%" >nul 2>&1
    exit /b 1
)

move "%ARCHIVE_ROOT%\%DIR_NAME%-main" "%DIR_NAME%" >nul
if errorlevel 1 (
    echo Failed to move the extracted source into %DIR_NAME%.
    if exist "%ARCHIVE_FILE%" del /q "%ARCHIVE_FILE%" >nul 2>&1
    if exist "%ARCHIVE_ROOT%" rmdir /s /q "%ARCHIVE_ROOT%" >nul 2>&1
    exit /b 1
)

if exist "%ARCHIVE_FILE%" del /q "%ARCHIVE_FILE%" >nul 2>&1
if exist "%ARCHIVE_ROOT%" rmdir /s /q "%ARCHIVE_ROOT%" >nul 2>&1
exit /b 0
