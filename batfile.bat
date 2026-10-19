@echo off
echo ==========================================================
echo           Sector-9: Echoes of The Watcher Setup
echo ==========================================================
echo.
echo Checking and installing required dependencies...
pip install pygame
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to install pygame automatically.
    echo Please check your internet connection or install python path variables.
    pause
    exit /b
)

echo.
echo Starting Python Execution environment...
python run_game.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [GAME CRASH DETECTED] python run_game.py closed with errors.
    echo Please view the traceback above to see what was missing.
    pause
)
