@echo off
REM Custodian Engine — kliknij dwukrotnie, by uruchomic backend + frontend.
REM Omija politykę wykonywania PowerShella dla tego jednego skryptu.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
