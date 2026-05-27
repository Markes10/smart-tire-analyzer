@echo off
setlocal EnableExtensions EnableDelayedExpansion
echo ~dp0 = %~dp0
set "ROOT=%~dp0"
echo RAW ROOT = %ROOT%
set "ROOT=%ROOT:~0,-1%"
echo STRIPPED ROOT = %ROOT%
echo Quoted: "%ROOT%"
pause
