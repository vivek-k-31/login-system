@echo off
python -m pip install -r requirements.txt
python seed.py
python app.py
pause
