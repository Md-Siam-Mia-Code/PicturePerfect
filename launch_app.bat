@echo off
setlocal

:: This script is called by the silent VBScript.
:: Its job is to activate the Conda environment and run the Python app.

:: --- Find Conda ---
set "CONDA_ACTIVATE_SCRIPT="
IF EXIST "%ProgramData%\anaconda3\Scripts\activate.bat" set "CONDA_ACTIVATE_SCRIPT=%ProgramData%\anaconda3\Scripts\activate.bat"
IF EXIST "%ProgramData%\miniconda3\Scripts\activate.bat" set "CONDA_ACTIVATE_SCRIPT=%ProgramData%\miniconda3\Scripts\activate.bat"
IF EXIST "%LOCALAPPDATA%\Programs\anaconda3\Scripts\activate.bat" set "CONDA_ACTIVATE_SCRIPT=%LOCALAPPDATA%\Programs\anaconda3\Scripts\activate.bat"
IF EXIST "%LOCALAPPDATA%\Programs\miniconda3\Scripts\activate.bat" set "CONDA_ACTIVATE_SCRIPT=%LOCALAPPDATA%\Programs\miniconda3\Scripts\activate.bat"

IF NOT DEFINED CONDA_ACTIVATE_SCRIPT (
    :: Cannot show an error as this runs in the background. It will just fail silently.
    EXIT /B 1
)

:: --- Activate Environment and Run App ---
:: Activate the base environment first to ensure conda commands work
CALL "%CONDA_ACTIVATE_SCRIPT%" base

:: Activate the project-specific environment
CALL conda activate PicturePerfect

:: Run the main Python application
python "%~dp0main.py"