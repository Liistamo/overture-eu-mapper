@echo off
REM Start over. Double-click to run.

cd /d "%~dp0\.."

echo.
echo   Removing cached boundaries ...
del /q scripts\data\boundaries_cache.geojson 2>nul
del /q scripts\data\boundaries_index.csv 2>nul

echo   Removing cached categories ...
del /q scripts\data\overture_categories.csv 2>nul

echo   Removing generated maps ...
del /q output\*.html 2>nul

echo.
echo   Clean. Run build-WINDOWS.bat to start over.
echo.
pause
