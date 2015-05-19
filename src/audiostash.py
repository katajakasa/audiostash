# -*- coding: utf-8 -*-

import json
import os
import settings
from common.tables import database_init
from tornado import web, ioloop
from sockjs.tornado import SockJSRouter, SockJSConnection


class AudioStashSock(SockJSConnection):
    clients = set()

    def __init__(self, session):
        self.authenticated = False
        super(AudioStashSock, self).__init__(session)

    def send_error(self, message, code):
        return self.send(json.dumps({
            'type': 'error',
            'data': {
                'code': code,
                'message': message
            }
        }))

    def send_message(self, mtype, message):
        return self.send(json.dumps({
            'type': mtype,
            'data': message,
        }))

    def on_open(self, info):
        self.authenticated = False
        self.clients.add(self)
        print("Connection accepted")

    def on_message(self, message):
        print("Message: {}.".format(message))

    def on_close(self):
        self.clients.remove(self)
        print("Connection closed")
        return super(AudioStashSock, self).on_close()


class IndexHandler(web.RequestHandler):
    def get(self):
        self.render(os.path.join(settings.PUBLIC_PATH, "index.html"))


if __name__ == '__main__':
    print("Starting AudioStash server on port {}.".format(settings.PORT))
    if settings.DEBUG:
        print("Public path = {}".format(settings.PUBLIC_PATH))
        print("Database path = {}".format(settings.DBFILE))

    # Set up database
    database_init(settings.DBFILE)

    # SockJS interface
    router = SockJSRouter(AudioStashSock, '/sock')

    # Index and static handlers
    handlers = [
        (r'/static/(.*)', web.StaticFileHandler, {'path': os.path.join(settings.PUBLIC_PATH, "static")}),
        (r'/partials/(.*)', web.StaticFileHandler, {'path': os.path.join(settings.PUBLIC_PATH, "partials")}),
        (r'/', IndexHandler)
    ] + router.urls
    
    conf = {
        'debug': settings.DEBUG,
    }

    # Start up everything
    app = web.Application(handlers, **conf)
    app.listen(settings.PORT, no_keep_alive=True)
    ioloop.IOLoop.instance().start()
    print("Stopping AudioStash server.")
