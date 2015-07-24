# -*- coding: utf-8 -*-

import json
import os
import settings
import mimetypes

from common.stashlog import StashLog

from passlib.hash import pbkdf2_sha256
from common.tables import database_init, session_get, User, Session, Track
from common.utils import generate_session
from tornado import web, ioloop, gen
from sockjs.tornado import SockJSRouter, SockJSConnection
from sqlalchemy.orm.exc import NoResultFound
import audiotranscode

log = None


class AudioStashSock(SockJSConnection):
    clients = set()

    def __init__(self, session):
        self.authenticated = False
        self.sid = None
        super(AudioStashSock, self).__init__(session)

    def send_error(self, mtype, message, code):
        msg = json.dumps({
            'type': mtype,
            'error': 1,
            'data': {
                'code': code,
                'message': message
            }
        })
        log.debug("Sending error {}".format(msg))
        return self.send(msg)

    def send_message(self, mtype, message):
        msg = json.dumps({
            'type': mtype,
            'error': 0,
            'data': message,
        })
        log.debug("Sending message {}".format(msg))
        return self.send(msg)

    def on_open(self, info):
        self.authenticated = False
        self.clients.add(self)
        log.debug("Connection accepted")

    def on_message(self, raw_message):
        # Load packet and parse as JSON
        try:
            message = json.loads(raw_message)
            log.debug("Message: {}.".format(raw_message))
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

                log.debug("Authenticated with '{}'.".format(self.sid))

                # Send login success message
                self.send_message('auth', {
                    'uid': user.id,
                    'sid': sid,
                    'level': user.level
                })
                return
            self.send_error('auth', "Invalid session", 403)
            log.debug("Authentication failed.")
            return

        elif packet_type == 'logout':
            # Remove session
            s = session_get()
            s.query(Session).filter_by(key=self.sid).delete()
            s.commit()

            # Dump out log
            log.debug("Logged out '{}'.".format(self.sid))

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
                log.debug("Logged in '{}'.".format(self.sid))

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
            log.debug("other")

    def on_close(self):
        self.clients.remove(self)
        log.debug("Connection closed")
        return super(AudioStashSock, self).on_close()


class IndexHandler(web.RequestHandler):
    def get(self):
        self.render(os.path.join(settings.PUBLIC_PATH, "index.html"))


class TrackHandler(web.RequestHandler):
    @web.asynchronous
    @gen.coroutine
    def get(self, song_id):
        # Find the song we want
        try:
            song = session_get().query(Track).filter_by(id=song_id).one()
        except NoResultFound:
            self.set_status(404)
            self.finish("404")
            return

        # See if we got range
        range_bytes = self.request.headers.get('Range')
        range_start = 0
        range_end = None
        if range_bytes:
            range_start, range_end = range_bytes[6:].split("-")
            range_end = None if range_end is "" else int(range_end)
            range_start = int(range_start)
            print("Streaming range: {} - {}".format(range_start, range_end))

        # Set streaming headers
        self.set_status(206)
        self.set_header("Accept-Ranges", "bytes")

        # Find content length and type
        if song.type in settings.NO_TRANSCODE_FORMATS:
            size = song.bytes_len
            self.set_header("Content-Type", mimetypes.guess_type("file://"+song.file)[0])
        else:
            size = song.bytes_tc_len
            self.set_header("Content-Type", "audio/mpeg")

        # Set range headers
        left = size - range_start
        if range_end:
            left = (range_end+1) - range_start
            self.set_header("Content-Range", "bytes {}-{}/{}".format(range_start, range_end, size))
        else:
            self.set_header("Content-Range", "bytes {}-{}/{}".format(range_start, size-1, size))

        # Set length headers (take into account range start point)
        self.set_header("Content-Length", left)

        print("Content-Length: {}".format(left))

        # Flush headers
        self.flush()

        # If the format is already mp3 or ogg, just stream out.
        # If format is something else, attempt to transcode.
        if song.type in settings.NO_TRANSCODE_FORMATS:
            log.debug("Direct streaming {}".format(song.file))
            with open(song.file, 'rb') as f:
                f.seek(range_start)

                # Just read as long as we have data to read.
                while left:
                    data = f.read(left if left < 8192 else 8192)
                    left -= len(data)
                    if data is None or len(data) == 0:
                        break
                    self.write(data)
                    self.flush()
        else:
            log.debug("Transcoding {}".format(song.file))
            pos = 0

            # Transcode from starting point
            at = audiotranscode.AudioTranscode()
            for data in at.transcode_stream(song.file, settings.TRANSCODE_FORMAT):
                bsize = len(data)
                if pos + bsize > range_start:
                    start = 0 if pos > range_start else range_start-pos
                    send = bsize-start if bsize-start < left else left
                    out = data[start:send]
                    self.write(out)
                    self.flush()
                    left -= len(out)
                    pos += len(out)
                else:
                    pos += bsize

                # Stop if no data left
                if left <= 0:
                    break

        # Flush the last bytes before finishing up.
        log.debug("Finished streaming {}".format(song.file))
        self.flush()
        self.finish()


if __name__ == '__main__':
    log = StashLog(debug=settings.DEBUG, level=settings.LOG_LEVEL, logfile=settings.STASH_LOGFILE)
    log.info("Starting AudioStash server on port {}.".format(settings.PORT))
    if settings.DEBUG:
        log.debug("Public path = {}".format(settings.PUBLIC_PATH))
        log.debug("Database path = {}".format(settings.DBFILE))

    # Set up database
    database_init(settings.DBFILE)

    # Set up mimetypes
    mimetypes.init()

    # SockJS interface
    router = SockJSRouter(AudioStashSock, '/sock')

    # Index and static handlers
    handlers = [
        (r'/static/(.*)', web.StaticFileHandler, {'path': os.path.join(settings.PUBLIC_PATH, "static")}),
        (r'/partials/(.*)', web.StaticFileHandler, {'path': os.path.join(settings.PUBLIC_PATH, "partials")}),
        (r'/track/(\d+)', TrackHandler),
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
