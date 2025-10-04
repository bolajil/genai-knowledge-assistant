@echo off
echo Listing available documents for improvement...
cd %~dp0
python list_documents.py
pause
