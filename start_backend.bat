@echo off
cd /d E:\Cognitive_Personal_Memory_Operating_System\backend

call ..\.venv\Scripts\activate.bat

uvicorn main:app --reload --reload-dir .

pause