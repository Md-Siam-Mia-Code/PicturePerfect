@echo off
setlocal

:: ============================================================================
:: == PicturePerfect - Automatic Installer for Windows with Conda
:: ============================================================================
:: This script will:
:: 1. Automatically find your Anaconda/Miniconda installation.
:: 2. Detect if you have an NVIDIA GPU.
:: 3. Create a dedicated Conda environment named 'PicturePerfect'.
:: 4. Install the correct version of PyTorch (GPU or CPU).
:: 5. Install all other required libraries.
:: 6. Launch the PicturePerfect Web UI.
:: ============================================================================

title PicturePerfect Installer

ECHO.
ECHO ========================================
ECHO  Welcome to the PicturePerfect Installer 
ECHO ========================================
ECHO.
ECHO This script will set up everything you need to run the application.
ECHO.
PAUSE

:: === STEP 1: Find Conda Installation ===
ECHO.
ECHO [*] Step 1 of 5: Searching for Anaconda/Miniconda...

set "CONDA_ACTIVATE_SCRIPT="
:: Search in common system-wide and user-specific locations
IF EXIST "%ProgramData%\anaconda3\Scripts\activate.bat" set "CONDA_ACTIVATE_SCRIPT=%ProgramData%\anaconda3\Scripts\activate.bat"
IF EXIST "%ProgramData%\miniconda3\Scripts\activate.bat" set "CONDA_ACTIVATE_SCRIPT=%ProgramData%\miniconda3\Scripts\activate.bat"
IF EXIST "%LOCALAPPDATA%\Programs\anaconda3\Scripts\activate.bat" set "CONDA_ACTIVATE_SCRIPT=%LOCALAPPDATA%\Programs\anaconda3\Scripts\activate.bat"
IF EXIST "%LOCALAPPDATA%\Programs\miniconda3\Scripts\activate.bat" set "CONDA_ACTIVATE_SCRIPT=%LOCALAPPDATA%\Programs\miniconda3\Scripts\activate.bat"

IF NOT DEFINED CONDA_ACTIVATE_SCRIPT (
    ECHO [!] ERROR: Anaconda/Miniconda installation not found in standard locations.
    ECHO Please install Anaconda/Miniconda and re-run this script.
    ECHO You can download it from: https://www.anaconda.com/download
    PAUSE
    EXIT /B 1
)
ECHO [+] Conda found at: %CONDA_ACTIVATE_SCRIPT%


:: === STEP 2: Detect NVIDIA GPU ===
ECHO.
ECHO [*] Step 2 of 5: Detecting NVIDIA GPU...

set GPU_DETECTED=0
:: Use nvidia-smi command, which is standard with NVIDIA drivers
nvidia-smi >nul 2>nul
IF %errorlevel% == 0 (
    ECHO [+] NVIDIA GPU Detected! Preparing to install PyTorch with CUDA support.
    set GPU_DETECTED=1
) ELSE (
    ECHO [-] No NVIDIA GPU detected. Preparing to install CPU-only PyTorch.
)


:: === STEP 3: Create and Activate Conda Environment ===
ECHO.
ECHO [*] Step 3 of 5: Setting up Conda environment 'PicturePerfect'...

:: Activate base env to ensure conda commands work
CALL "%CONDA_ACTIVATE_SCRIPT%" base

:: Check if the environment already exists
conda env list | findstr /I /C:"PicturePerfect" >nul
IF %errorlevel% == 0 (
    ECHO [+] Environment 'PicturePerfect' already exists. Activating...
) ELSE (
    ECHO [*] Creating new environment 'PicturePerfect' with Python 3.7. This may take a minute...
    conda create -n PicturePerfect python=3.7 -y
    IF %errorlevel% NEQ 0 (
        ECHO [!] ERROR: Failed to create the Conda environment. Please check your Conda installation.
        PAUSE
        EXIT /B 1
    )
)

:: Activate the project environment
ECHO [*] Activating 'PicturePerfect' environment...
CALL conda activate PicturePerfect


:: === STEP 4: Install Dependencies (PyTorch + requirements.txt) ===
ECHO.
ECHO [*] Step 4 of 5: Installing Python libraries...
ECHO This is the longest step and may take several minutes depending on your internet connection.
ECHO.

IF %GPU_DETECTED% == 1 (
    GOTO InstallGpuPyTorch
) ELSE (
    GOTO InstallCpuPyTorch
)

:InstallGpuPyTorch
ECHO [*] Installing PyTorch with CUDA 11.8. Conda will handle compatibility.
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia -y
IF %errorlevel% NEQ 0 (
    ECHO [!] ERROR: Failed to install PyTorch with CUDA support.
    ECHO Please ensure your NVIDIA drivers are up to date and try again.
    PAUSE
    EXIT /B 1
)
GOTO InstallPip

:InstallCpuPyTorch
ECHO [*] Installing CPU-only version of PyTorch.
conda install pytorch torchvision torchaudio cpuonly -c pytorch -y
IF %errorlevel% NEQ 0 (
    ECHO [!] ERROR: Failed to install CPU-only PyTorch.
    PAUSE
    EXIT /B 1
)
GOTO InstallPip

:InstallPip
ECHO.
ECHO [*] Installing remaining dependencies from requirements.txt...
pip install -r requirements.txt
IF %errorlevel% NEQ 0 (
    ECHO [!] ERROR: Failed to install dependencies from requirements.txt.
    PAUSE
    EXIT /B 1
)


:: === STEP 5: Launch PicturePerfect ===
ECHO.
ECHO ==================================
ECHO  [+] Setup Complete!
ECHO ==================================
ECHO.
ECHO [*] Step 5 of 5: Launching PicturePerfect Web UI...
ECHO You can access the UI in your web browser at the address shown below.
ECHO Press CTRL+C in this window to close the application.
ECHO.

python main.py

ECHO.
ECHO PicturePerfect has been closed.
PAUSE