@echo off
title Virtual Mic Server
color 0A
echo =========================================
echo    Starting Virtual Mic Receiver...
echo =========================================
echo.

:: Switch to the current script directory
cd /d "%~dp0"

:: Install requirements
py -m pip install zeroconf pystray pillow numpy customtkinter > nul 2>&1

:: Run the Python server
py server.py

:: If the server crashes, this keeps the window open so you can read the error
pause