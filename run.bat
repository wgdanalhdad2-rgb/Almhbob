@echo off
echo Installing requirements...
pip install -r requirements.txt

echo Starting the server...
uvicorn main:app --reload
pause
