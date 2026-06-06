@echo off
title Virtual Mic Server
color 0A
echo =========================================
echo    Starting Virtual Mic Receiver...
echo =========================================
echo.

:: Switch to the correct drive just in case
D:

:: Navigate to your project folder
cd "D:\Android Projects\VirtualMic"

:: Install requirements
py -m pip install zeroconf pystray pillow numpy customtkinter > nul 2>&1

:: Run the Python server
py server.py

:: If the server crashes, this keeps the window open so you can read the error
pause