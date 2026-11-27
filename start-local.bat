@echo off
cd /d "%~dp0"
echo Menjalankan Property 360 VR Server di http://127.0.0.1:8080/ ...
start "" http://127.0.0.1:8080/
python dev_server.py
pause
