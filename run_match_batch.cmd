@echo off
echo ================================
echo JOBBOT BATCH MATCHER STARTED
echo ================================

set BASE=C:\Users\D\.openclaw\workspace\jobbot
set JOBS=%BASE%\jobs
set OUT=%BASE%\output

for %%F in (%JOBS%\*.txt) do (
  echo Processing %%~nxF

  powershell -ExecutionPolicy Bypass -File "%BASE%\build_match_prompt.ps1" "%%F" "%OUT%\%%~nF_match.json"
)

echo ================================
echo BATCH COMPLETE
echo ================================
pause
