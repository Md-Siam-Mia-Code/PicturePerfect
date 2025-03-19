@echo off

:: Activate the conda environment for PicturePerfect
CALL "C:\ProgramData\<your anaconda distribution name>\Scripts\activate.bat" PicturePerfect

:: Navigate to the PicturePerfect directory (Change path according to yours)
cd /D path/to/your/PicturePerfect

:: Run PicturePerfect
uvicorn main:app --host 127.0.0.1 --port 3015
