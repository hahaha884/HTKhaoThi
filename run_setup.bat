@echo off
echo Dang cap nhat co so du lieu (Database)...
call .venv\Scripts\activate
python manage.py makemigrations matrix
python manage.py migrate
echo.
echo Dang tao tai khoan Hieu truong...
python create_bgh.py
echo.
echo HOAN TAT! Ban co the tat cua so nay va F5 lai trang web.
pause
