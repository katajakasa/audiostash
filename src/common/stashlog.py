# -*- coding: utf-8 -*-

import sys
from datetime import datetime
import isodate


class StashLog(object):
    def __init__(self, debug=False, level=0, logfile=None):
        self.debugmode = debug
        self.level = level
        self.logfile = logfile

    @staticmethod
    def timestamp():
        return isodate.datetime_isoformat(datetime.now())

    def format(self, code, msg, ip=None):
        if ip:
            return "[{}][{}][{}] {}".format(code, self.timestamp(), ip, msg)
        else:
            return "[{}][{}] {}".format(code, self.timestamp(), msg)

    def write(self, code, msg, ip=None):
        if self.debugmode:
            print(self.format(code, msg, ip=ip))
            sys.stdout.flush()
        elif self.logfile:
            with open(self.logfile, 'ab') as f:
                f.write(self.format(code, "{}\n".format(msg), ip=ip))
                f.flush()

    def debug(self, msg, ip=None):
        if self.level <= 1:
            self.write('D', msg, ip=ip)

    def info(self, msg, ip=None):
        if self.level < 2:
            self.write('I', msg, ip=ip)

    def warning(self, msg, ip=None):
        if self.level < 3:
            self.write('W', msg, ip=ip)

    def error(self, msg, ip=None):
        if self.level < 4:
            self.write('E', msg, ip=ip)
