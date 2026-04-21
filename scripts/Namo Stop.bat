@echo off
title Namo Core — Stopping...
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File "%~dp0namo_stop_all.ps1"
pause
