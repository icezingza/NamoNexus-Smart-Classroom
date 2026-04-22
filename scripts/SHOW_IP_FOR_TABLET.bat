@echo off
title NamoNexus Tablet Helper
color 0E

echo ------------------------------------------
echo    NAMO NEXUS - TABLET GUIDE
echo ------------------------------------------
echo.
echo Please look for the IPv4 Address below:
echo.

:: ดึงค่า IP แบบมาตรฐานที่สุด
ipconfig | findstr "IPv4"

echo.
echo ------------------------------------------
echo STEP 1: Look at the number above (e.g., 192.168.1.15)
echo STEP 2: Open Chrome on your TABLET
echo STEP 3: Type: http://[THE_NUMBER_ABOVE]:5173
echo.
echo Example: http://192.168.1.15:5173
echo.
echo ------------------------------------------
echo DO NOT CLOSE THIS WINDOW while using Tablet.
echo.
pause
