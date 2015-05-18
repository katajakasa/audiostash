# -*- coding: utf-8 -*-

import json
import os
import settings
from common.tables import database_init
from tornado import web, ioloop
from sockjs.tornado import SockJSRouter, SockJSConnection


class AudioStashSock(SockJSConnection):
    clients = set()

    def __init__(self):
        self.authenticated = False
        super(AudioStashSock, self).__init__(self)

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
        print(info)

    def on_message(self, message):
        print("Message: {}.".format(message))

    def on_close(self):
        self.clients.remove(self)
        return super(AudioStashSock, self).on_close()


class IndexHandler(web.RequestHandler):
    def get(self):
        self.render(os.path.join(settings.TEMPLATE_PATH, "index.html"))


if __name__ == '__main__':
    print("Starting AudioStash server on port {}.".format(settings.PORT))
    if settings.DEBUG:
        print("Static path = {}".format(settings.STATIC_PATH))
        print("Template path = {}".format(settings.TEMPLATE_PATH))
        print("Database path = {}".format(settings.DBFILE))

    # Set up database
    database_init(settings.DBFILE)

    # SockJS interface
    router = SockJSRouter(AudioStashSock, '/sock')

    # Index and static handlers
    handlers = [
        (r'/', IndexHandler),
    ] + router.urls
    
    conf = {
        'debug': settings.DEBUG,
        'static_path': settings.STATIC_PATH,
        'static_prefix': "/static",
    }

    # Start up everything
    app = web.Application(handlers, **conf)
    app.listen(settings.PORT, no_keep_alive=True)
    ioloop.IOLoop.instance().start()
    print("Stopping AudioStash server.")
