@echo off
cd /d "%~dp0"
start /min "" "env\pythonw.exe" "env\converter_gui.py" "%~dp0"
exit
