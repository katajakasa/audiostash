# -*- coding: utf-8 -*-

from audiostash import settings
import mimetypes
import logging
import argparse
import sys

from audiostash.common.tables import database_init
from tornado import web, ioloop
from sockjs.tornado import SockJSRouter
from audiostash.webui.sockethandler import AudioStashSock
from audiostash.webui.trackhandler import TrackHandler
from audiostash.webui.coverhandler import CoverHandler


if __name__ == '__main__':
    # Handle arguments
    parser = argparse.ArgumentParser(description="Audiostash Web UI server")
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
        logging.basicConfig(filename=settings.STASH_LOGFILE,
                            filemode='wb',
                            level=level,
                            format=log_format,
                            datefmt=log_datefmt)

    log = logging.getLogger(__name__)

    # Some log info
    log.info(u"Starting AudioStash server.")
    log.info(u"Public path = %s", settings.PUBLIC_PATH)
    log.info(u"Server port = %s", settings.PORT)

    # Set up database
    database_init(settings.DATABASE_CONFIG)

    # Set up mimetypes
    mimetypes.init()

    # SockJS interface
    router = SockJSRouter(AudioStashSock, '/sock')

    # Index and static handlers
    handlers = router.urls + [
        (r'/track/([a-z0-9]+)/(\d+).mp3$', TrackHandler),
        (r'/cover/([a-z0-9]+)/(\d)/(\d+)$', CoverHandler),
        (r'/(.*)$', web.StaticFileHandler, {'path': settings.PUBLIC_PATH, 'default_filename': 'index.html'}),
    ]

    conf = {
        'debug': settings.DEBUG,
    }

    # Start up everything
    app = web.Application(handlers, **conf)
    app.listen(settings.PORT)
    loop = ioloop.IOLoop.instance()
    try:
        loop.start()
    except KeyboardInterrupt:
        loop.stop()
    log.info(u"Stopping AudioStash server.")
