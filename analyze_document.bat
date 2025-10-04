@echo off
echo Document Analysis Tool
echo.

IF "%~1"=="" (
    echo Please provide a document name to analyze.
    echo Usage: analyze_document.bat [document_name]
    echo Example: analyze_document.bat AWS
    goto :EOF
)

echo Analyzing document: %1
python analyze_document.py %1
pause
