# -*- coding: utf-8 -*-

import json
import os
import settings

from common.stashlog import StashLog

from passlib.hash import pbkdf2_sha256
from common.tables import database_init, session_get, User, Session
from common.utils import generate_session
from tornado import web, ioloop
from sockjs.tornado import SockJSRouter, SockJSConnection
from sqlalchemy.orm.exc import NoResultFound


class AudioStashSock(SockJSConnection):
    clients = set()

    def __init__(self, session):
        self.authenticated = False
        self.sid = None
        super(AudioStashSock, self).__init__(session)

    def send_error(self, mtype, message, code):
        return self.send(json.dumps({
            'type': mtype,
            'error': 1,
            'data': {
                'code': code,
                'message': message
            }
        }))

    def send_message(self, mtype, message):
        return self.send(json.dumps({
            'type': mtype,
            'error': 0,
            'data': message,
        }))

    def on_open(self, info):
        self.authenticated = False
        self.clients.add(self)
        self.log.debug("Connection accepted")

    def on_message(self, raw_message):
        # Load packet and parse as JSON
        try:
            message = json.loads(raw_message)
            self.log.debug("Message: {}.".format(raw_message))
        except ValueError:
            self.send_error('none', "Invalid JSON", 500)
            return

        # Handle packet by type
        packet_type = message.get('type', '')
        packet_msg = message.get('message', {})
        if packet_type == 'auth':
            sid = packet_msg.get('sid', '')

            s = session_get()
            user = None
            session = None
            try:
                session = s.query(Session).filter_by(key=sid).one()
                user = s.query(User).filter_by(id=session.user).one()
            except NoResultFound:
                pass

            # Session found with token.
            if session and user:
                self.sid = sid
                self.authenticated = True

                self.log.debug("Authenticated with '{}'.".format(self.sid))

                # Send login success message
                self.send_message('auth', {
                    'uid': user.id,
                    'sid': sid,
                    'level': user.level
                })
                return
            self.send_error('auth', "Invalid session", 403)
            self.log.debug("Authentication failed.")
            return

        elif packet_type == 'logout':
            # Remove session
            s = session_get()
            s.query(Session).filter_by(key=self.sid).delete()
            s.commit()

            # Dump out log
            self.log.debug("Logged out '{}'.".format(self.sid))

            # Disauthenticate & clear session ID
            self.authenticated = False
            self.sid = None
            return

        elif packet_type == 'login':
            username = packet_msg.get('username', '')
            password = packet_msg.get('password', '')

            s = session_get()
            user = None
            try:
                user = s.query(User).filter_by(username=username).one()
            except NoResultFound:
                pass

            # If user exists and password matches, pass onwards!
            if user and pbkdf2_sha256.verify(password, user.password):
                session_id = generate_session()

                # Add new session
                ses = Session(key=session_id, user=user.id)
                s.add(ses)
                s.commit()

                # Mark connection as authenticated, and save session id
                self.sid = session_id
                self.authenticated = True

                # Dump out log
                self.log.debug("Logged in '{}'.".format(self.sid))

                # TODO: Cleanup old sessions

                # Send login success message
                self.send_message('login', {
                    'uid': user.id,
                    'sid': session_id,
                    'level': user.level
                })
                return

            self.send_error('login', "Invalid username or password", 403)
            return
        else:
            self.log.debug("other")

    def on_close(self):
        self.clients.remove(self)
        self.log.debug("Connection closed")
        return super(AudioStashSock, self).on_close()


class IndexHandler(web.RequestHandler):
    def get(self):
        self.render(os.path.join(settings.PUBLIC_PATH, "index.html"))


if __name__ == '__main__':
    log = StashLog(debug=settings.DEBUG, level=settings.LOG_LEVEL, logfile=settings.STASH_LOGFILE)
    log.info("Starting AudioStash server on port {}.".format(settings.PORT))
    if settings.DEBUG:
        log.debug("Public path = {}".format(settings.PUBLIC_PATH))
        log.debug("Database path = {}".format(settings.DBFILE))

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
    app.listen(settings.PORT,  no_keep_alive=True)
    ioloop.IOLoop.instance().start()
    log.info("Stopping AudioStash server.")
