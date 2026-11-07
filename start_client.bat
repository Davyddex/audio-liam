@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" client.py %*
) else (
    py -3 client.py %*
)
echo.
pause
popd
endlocal
