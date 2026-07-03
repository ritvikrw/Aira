@echo off
title AIRA Backend
cd /d C:\Users\Mani\Desktop\RECEP\backend\api
set PYTHONUNBUFFERED=1
if exist "C:\Users\Mani\Desktop\RECEP\backend\.env" (
    for /f "usebackq tokens=1,* delims==" %%a in ("C:\Users\Mani\Desktop\RECEP\backend\.env") do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
    )
)
echo Starting AIRA Backend on port 8001...
echo DB: %DATABASE_URL%
C:\Users\Mani\AppData\Local\Programs\Python\Python312\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
pause
