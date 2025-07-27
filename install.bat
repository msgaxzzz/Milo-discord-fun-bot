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
set "DIR_NAME=Milo-discord-fun-bot"

:: Check if git exists
where git >nul 2>&1
if errorlevel 1 (
    echo Git is not installed or not in PATH. Please install git first.
    pause
    exit /b 1
)

:: Clone repo if not exist
if not exist "%DIR_NAME%" (
    echo Cloning repository from %REPO_URL%...
    git clone "%REPO_URL%"
    if errorlevel 1 (
        echo Failed to clone repository.
        pause
        exit /b 1
    )
) else (
    echo Directory %DIR_NAME% already exists, skipping clone.
)

cd "%DIR_NAME%" || (
    echo Cannot enter directory %DIR_NAME%.
    pause
    exit /b 1
)

:: Find Python 3.7+
set PYTHON_BIN=
for %%P in (python3.11 python3.10 python3.9 python3.8 python3.7 python) do (
    for /f "tokens=2 delims= " %%V in ('%%P --version 2^>^&1') do (
        set "VER=%%V"
        for /f "tokens=1,2 delims=." %%A in ("!VER!") do (
            set "MAJOR=%%A"
            set "MINOR=%%B"
            if !MAJOR! GEQ 3 (
                if !MINOR! GEQ 7 (
                    set PYTHON_BIN=%%P
                    goto foundpython
                )
            )
        )
    )
)

:foundpython
if not defined PYTHON_BIN (
    echo No compatible Python (>=3.7) found. Please install Python 3.7 or higher.
    pause
    exit /b 1
)
echo Found Python: %PYTHON_BIN%

:: Check pip
%PYTHON_BIN% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip not found, installing pip...
    %PYTHON_BIN% -m ensurepip --upgrade
)

:: Install requirements
echo Installing dependencies from requirements.txt...
%PYTHON_BIN% -m pip install --upgrade pip
%PYTHON_BIN% -m pip install -r requirements.txt

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
echo   %PYTHON_BIN% main.py
echo Update log: https://github.com/msgaxzzz/Milo-discord-fun-bot/blob/main/CHANGELOG.md

pause
