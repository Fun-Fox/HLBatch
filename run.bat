@echo off
:: 设置 Python 解释器路径（直接使用虚拟环境中的 python.exe）
set PYTHON_EXE=C:\ProgramData\miniconda3\envs\ComfyUI\python.exe

:: 设置脚本路径
set SCRIPT_PATH=D:\PycharmProjects\HaiLuoApi\hailuo_ui.py

:: 使用 Python 直接运行 streamlit（不需要激活环境）
%PYTHON_EXE% -m streamlit run "%SCRIPT_PATH%"

:: 暂停（可选）
pause