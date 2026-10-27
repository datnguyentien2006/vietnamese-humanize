@echo off
chcp 65001 >nul
title vi-humanizer - restart teacher local
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restart_teacher_local.ps1"
pause
