@echo off
echo ==============================================
echo   📤 Pushing Protoptype branch to main...
echo ==============================================
echo.

:: 1. Add all changes to git
echo [1/3] Adding files to git...
git add .

:: 2. Commit changes
echo.
echo [2/3] Committing changes...
git commit -m "Organize lab files into subdirectories and sync Lab 2.1"

:: 3. Force push Protoptype to main
echo.
echo [3/3] Pushing to main branch on GitHub...
git push origin Protoptype:main --force

echo.
echo ==============================================
echo   ✅ Push complete!
echo ==============================================
pause
