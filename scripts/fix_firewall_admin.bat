@echo off
netsh advfirewall firewall delete rule name="Namo Core API 8000" >nul 2>&1
netsh advfirewall firewall add rule name="Namo Core API 8000" dir=in action=allow protocol=TCP localport=8000
echo.
echo ===================================
echo  Firewall rule added for port 8000
echo ===================================
pause
