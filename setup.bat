@echo off
echo ================================
echo Heyllo.ai Backend Setup
echo ================================
echo.

REM Check if .env exists
if exist .env (
    echo [OK] .env file found
) else (
    echo [!] Creating .env file from template...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please update the .env file with your actual values:
    echo   - DATABASE_URL: Your PostgreSQL connection string
    echo   - SECRET_KEY: Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    echo.
    pause
)

echo.
echo [1] Checking Python and pip...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2] Creating virtual environment...
if not exist venv (
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

echo.
echo [3] Activating virtual environment...
call venv\Scripts\activate

echo.
echo [4] Installing dependencies...
pip install -r requirements.txt

echo.
echo [5] Setting up database...
echo    Run migrations? (This will create database tables)
choice /C YN /M "Continue with database setup"
if errorlevel 2 goto skip_db
if errorlevel 1 goto setup_db

:setup_db
alembic upgrade head
if errorlevel 1 (
    echo [ERROR] Database migration failed!
    echo Please check your DATABASE_URL in .env file
    pause
    exit /b 1
)
echo [OK] Database tables created
goto done_db

:skip_db
echo [SKIPPED] Database setup skipped

:done_db
echo.
echo ================================
echo Setup Complete!
echo ================================
echo.
echo Next steps:
echo 1. Update .env file with your actual credentials
echo 2. Run the backend with: python -m app.main
echo    OR: uvicorn app.main:app --reload
echo.
echo API Documentation will be available at:
echo   - http://localhost:8000/docs
echo   - http://localhost:8000/redoc
echo.
pause
