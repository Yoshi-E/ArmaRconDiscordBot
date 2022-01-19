import traceback
import sys
import os

import logging
from logging.handlers import RotatingFileHandler


def print_exc():
    log.error(traceback.format_exc())

_log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
_logFile = os.path.dirname(os.path.realpath(__file__))+"/error.log"
print("Log file path: '{}'".format(_logFile))
_stdout_handler = logging.StreamHandler(sys.stdout)
_my_handler = RotatingFileHandler(_logFile, mode='a', maxBytes=10*1000000, backupCount=10, encoding=None, delay=0)
_my_handler.setFormatter(_log_formatter)
_my_handler.setLevel(logging.INFO)

log = logging.getLogger("core")
log.setLevel(logging.INFO)
log.addHandler(_my_handler)
log.addHandler(_stdout_handler)
log.print_exc = print_exc
#print(dir(log))
