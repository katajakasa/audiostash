# -*- coding: utf-8 -*-

import argparse
import signal
import os
import sys
from audiostash import settings
import logging

from audiostash.common.tables import database_init
from audiostash.scand.scanner import Scanner


def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

if __name__ == '__main__':
    # Handle arguments
    parser = argparse.ArgumentParser(description="Audiostash Indexer Daemon")
    args = parser.parse_args()

    # Find correct log level
    level = {
        0: logging.DEBUG,
        1: logging.INFO,
        2: logging.WARNING,
        3: logging.ERROR,
        4: logging.CRITICAL
    }[settings.LOG_LEVEL]

    # Set up the global log
    log_format = '[%(asctime)s] %(message)s'
    log_datefmt = '%d.%m.%Y %I:%M:%S'
    if settings.DEBUG:
        logging.basicConfig(stream=sys.stdout,
                            level=level,
                            format=log_format,
                            datefmt=log_datefmt)
    else:
        logging.basicConfig(filename=settings.SCAND_LOGFILE,
                            filemode='ab',
                            level=level,
                            format=log_format,
                            datefmt=log_datefmt)

    log = logging.getLogger(__name__)

    # Make sure the cover cache directory exists
    ensure_dir(settings.COVER_CACHE_DIRECTORY)
    ensure_dir(settings.MUSIC_CACHE_DIRECTORY)

    # Init database and bootstrap the scanner
    database_init(settings.DATABASE_CONFIG)
    scanner = Scanner()

    # There should be okay on windows ...
    def sig_handler(signum, frame):
        log.info(u"Caught signal %d, quitting ...", signum)
        scanner.stop()
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    # ... while these are not. Try for linux' sake, though.
    try:
        signal.signal(signal.SIGHUP,  sig_handler)
        signal.signal(signal.SIGQUIT, sig_handler)
    except AttributeError:
        pass

    # Just run as long as possible, then exit with 0 status.
    scanner.run()
    exit(0)
