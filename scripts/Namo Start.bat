@echo off
title Namo Core — Starting...
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File "%~dp0namo_start_all.ps1"
pause
