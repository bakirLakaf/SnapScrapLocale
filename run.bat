@echo off
REM Run SnapScrap from CMD - sets UTF-8 so Arabic displays correctly
chcp 65001 >nul
cd /d "%~dp0"

if "%~1"=="" (
    python SnapScrap.py help
    goto :eof
)

if /i "%~1"=="en" (
    set SNAPSCRAP_LANG=en
    shift
    if "%~1"=="" (
        python SnapScrap.py help
        goto :eof
    )
)

python SnapScrap.py %*
