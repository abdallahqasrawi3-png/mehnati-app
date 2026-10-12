@echo off
rem Mehnaty: start database, API and app with one command. Add -Demo to load demo data.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch.ps1" %*
