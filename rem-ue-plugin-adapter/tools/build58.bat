@echo off
REM Local convenience wrapper - adjust PLUGIN and CONFIG for your machine
set PLUGIN=MyPlugin
rem Point CONFIG at the PLUGIN's external local.json (see README.md first-time setup)
set CONFIG=
python "%~dp0build_plugin.py" -n %PLUGIN% --config "%CONFIG%" -v 5.8 %*
