@echo off
setlocal

:: Create a base virtual environment in the current folder
set TEMPLATE_DIR=%CD%\venv

echo Creating template virtual environment in:
echo %TEMPLATE_DIR%

python -m venv "%TEMPLATE_DIR%"

:: (Optional) Activate and upgrade pip
call "%TEMPLATE_DIR%\Scripts\activate.bat"
echo Upgrading pip...
python -m pip install --upgrade pip

deactivate
echo Done.

endlocal
pause
