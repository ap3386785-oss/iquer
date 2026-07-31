@echo off
title Aegis Spirit - Smart Alcohol Verification System
echo ==========================================================
echo  Aegis Spirit System Setup & Startup Script
echo ==========================================================
echo.
echo [1/2] Installing required Python libraries...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Some packages failed to install. Make sure Python is in your PATH.
)
echo.
echo [2/2] Launching Flask server backend...
echo.
python backend/app.py
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start Flask server.
)
pause
