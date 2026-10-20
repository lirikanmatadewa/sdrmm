@echo off
if not exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" (
    echo Visual Studio 2022 Community with Desktop development with C++ is required. 1>&2
    exit /b 1
)
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
exit /b %errorlevel%