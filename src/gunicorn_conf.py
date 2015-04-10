bind = "0.0.0.0:80"
workers = 2
user = 'apex'
accesslog = 'access.log'
errorlog = 'error.log'
access_log_format = '%(h)s %(l)s %(u)s %(t)s %(D)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s'

