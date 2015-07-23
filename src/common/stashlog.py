# -*- coding: utf-8 -*-

import sys
from datetime import datetime


class StashLog(object):
    def __init__(self, debug=False, level=0, logfile=None):
        self.debugmode = debug
        self.level = level
        self.logfile = logfile

    @staticmethod
    def timestamp():
        return datetime.now().isoformat()

    def format(self, code, msg):
        return "[{}][{}] {}".format(code, self.timestamp(), msg)

    def write(self, code, msg):
        if self.debugmode:
            print(self.format(code, msg))
            sys.stdout.flush()
        elif self.logfile:
            with open(self.logfile, 'ab') as f:
                f.write(self.format(code, "{}\n".format(msg)))
                f.flush()

    def debug(self, msg):
        if self.level <= 1:
            self.write('D', msg)

    def info(self, msg):
        if self.level < 2:
            self.write('I', msg)

    def warning(self, msg):
        if self.level < 3:
            self.write('W', msg)

    def error(self, msg):
        if self.level < 4:
            self.write('E', msg)
