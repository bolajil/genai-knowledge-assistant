@echo off

echo Testing Weaviate connection...
py test_weaviate_connection.py
if %errorlevel% == 0 (
    echo Connection test successful!
) else (
    echo Connection test failed!
)
pause
