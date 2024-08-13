# gunicorn.conf.py
import multiprocessing

bind = "0.0.0.0:4000"
workers = multiprocessing.cpu_count() * 2 + 1
loglevel = 'info'
errorlog = '-'  # 표준 에러를 로깅하도록 설정
accesslog = '-'  # 표준 출력으로 액세스 로그를 보냄
timeout = 120