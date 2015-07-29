# -*- coding: utf-8 -*-

import json
import settings
import os
import mimetypes

from common import audiotranscode
from common.stashlog import StashLog

from passlib.hash import pbkdf2_sha256
from common.tables import \
    session_get, database_init, Artist, Album, Cover, Directory, Playlist, PlaylistItem, \
    Track, Setting, Session, User
from common.utils import generate_session, to_isodate, from_isodate, utc_now
from tornado import web, ioloop, gen
from tornado.httputil import HTTPOutputError
from sockjs.tornado import SockJSRouter, SockJSConnection
from sqlalchemy.orm.exc import NoResultFound

log = None


class AudioStashSock(SockJSConnection):
    clients = set()

    def __init__(self, session):
        self.authenticated = False
        self.sid = None
        self.ip = None
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
        log.debug("Sending error {}".format(msg), ip=self.ip)
        return self.send(msg)

    def send_message(self, mtype, message):
        msg = json.dumps({
            'type': mtype,
            'error': 0,
            'data': message,
        })
        log.debug("Sending message {}".format(msg), ip=self.ip)
        return self.send(msg)

    def on_open(self, info):
        self.authenticated = False
        self.ip = info.ip
        self.clients.add(self)
        log.debug("Connection accepted", ip=self.ip)

    def on_auth_msg(self, packet_msg):
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

            log.info("Authenticated with '{}'.".format(self.sid), ip=self.ip)

            # Send login success message
            self.send_message('auth', {
                'uid': user.id,
                'sid': sid,
                'level': user.level
            })
            return
        self.send_error('auth', "Invalid session", 403)
        log.info("Authentication failed.", ip=self.ip)

    def on_login_msg(self, packet_msg):
        username = packet_msg.get('username', '')
        password = packet_msg.get('password', '')

        s = session_get()
        try:
            user = s.query(User).filter_by(username=username).one()
        except NoResultFound:
            self.send_error('login', 'Incorrect username or password', 401)
            return

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
            log.info("Logged in '{}'.".format(self.sid), ip=self.ip)

            # TODO: Cleanup old sessions

            # Send login success message
            self.send_message('login', {
                'uid': user.id,
                'sid': session_id,
                'level': user.level
            })
        else:
            self.send_error('login', 'Incorrect username or password', 401)
            return

    def on_logout_msg(self, packet_msg):
        # Remove session
        s = session_get()
        s.query(Session).filter_by(key=self.sid).delete()
        s.commit()

        # Dump out log
        log.info("Logged out '{}'.".format(self.sid), ip=self.ip)

        # Disauthenticate & clear session ID
        self.authenticated = False
        self.sid = None

    def on_sync_msg(self, packet_msg):
        if not self.authenticated:
            return

        query = packet_msg.get('query', '')
        if query == 'request':
            name = packet_msg.get('table')

            # Attempt to parse timestamp received from the client.
            try:
                remote_ts = from_isodate(packet_msg.get('ts'))
            except:
                self.send_error('sync', "Invalid timestamp", 400)
                return

            # Find table model that matches the name
            try:
                table = {
                    'artist': Artist,
                    'album': Album,
                    'track': Track
                }[name]
            except KeyError:
                self.send_error('sync', "Invalid table name", 400)
                return

            # Send message containing all new data in the table
            self.send_message('sync', {
                'query': 'request',
                'table': name,
                'ts': to_isodate(utc_now()),
                'data': [t.serialize() for t in session_get().query(table).filter(table.updated > remote_ts)]
            })
            return

    def on_unknown_msg(self, packet_msg):
        log.debug("Unknown or nonexistent packet type!", ip=self.ip)

    def on_message(self, raw_message):
        # Load packet and parse as JSON
        try:
            message = json.loads(raw_message)
        except ValueError:
            self.send_error('none', "Invalid JSON", 400)
            return

        # Handle packet by type
        packet_type = message.get('type', '')
        packet_msg = message.get('message', {})

        # Censor login packets for obvious reasons ...
        if type != 'login':
            log.debug("Message: {}.".format(raw_message), ip=self.ip)
        else:
            log.debug("Message: **login**", ip=self.ip)

        # Find and run callback
        cbs = {
            'auth': self.on_auth_msg,
            'login': self.on_login_msg,
            'logout': self.on_logout_msg,
            'sync': self.on_sync_msg,
            'unknown': self.on_unknown_msg
        }
        cbs[packet_type if packet_type in cbs else 'unknown'](packet_msg)

    def on_close(self):
        self.clients.remove(self)
        log.debug("Connection closed", ip=self.ip)
        return super(AudioStashSock, self).on_close()


class CoverHandler(web.RequestHandler):
    def get(self, session_id, size_flag, cover_id):
        # Make sure session is valid
        try:
            session_get().query(Session).filter_by(key=session_id).one()
        except NoResultFound:
            self.set_status(401)
            self.finish("401")
            return

        if size_flag == "0":
            cover_file = os.path.join(settings.COVER_CACHE_DIRECTORY, "{}.jpg".format(cover_id))
        else:
            # Find the cover we want
            try:
                cover = session_get().query(Cover).filter_by(id=cover_id).one()
            except NoResultFound:
                self.set_status(404)
                self.finish("404")
                return

            # Make sure we have a filename
            if not cover.file:
                self.set_status(404)
                self.finish("404")
                return

            cover_file = cover.file

        # Make sure the file exists on disk
        if not os.path.isfile(cover_file):
            self.set_status(404)
            self.finish("404")
            return

        # Just pick content type and dump out the file.
        self.set_header("Content-Type", mimetypes.guess_type("file://"+cover_file)[0])
        with file(cover_file, 'rb') as f:
            while True:
                data = f.read(8192)
                if not data:
                    break
                self.write(data)
        self.finish()


class TrackHandler(web.RequestHandler):
    @web.asynchronous
    @gen.coroutine
    def get(self, session_id, song_id):
        # Make sure session is valid
        try:
            session_get().query(Session).filter_by(key=session_id).one()
        except NoResultFound:
            self.set_status(401)
            self.finish("401")
            return

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

        # Set streaming headers
        self.set_status(206)
        self.set_header("Accept-Ranges", "bytes")

        # Find content length and type
        is_transcode_op = (song.type in settings.NO_TRANSCODE_FORMATS)
        if is_transcode_op:
            size = song.bytes_len
            self.set_header("Content-Type", mimetypes.guess_type("file://"+song.file)[0])
        else:
            size = song.bytes_tc_len
            self.set_header("Content-Type", "audio/mpeg")

        # Set end range
        if not range_end or range_end >= size:
            range_end = size-1

        # Limit single request size for non-transcode ops
        # 10M ought to be enough for everybody
        if not is_transcode_op and range_end - range_start > 10485760:
            range_end = range_start + 10485760 - 1

        # Make sure range_start and range_end are withing size limits
        if range_start >= size:
            self.set_status(416)
            self.finish()
            return

        # Set range headers
        left = (range_end+1) - range_start
        self.set_header("Content-Length", left)
        self.set_header("Content-Range", "bytes {}-{}/{}".format(range_start, range_end, size))
        self.flush()

        # If the format is already mp3 or ogg, just stream out.
        # If format is something else, attempt to transcode.
        if song.type in settings.NO_TRANSCODE_FORMATS:
            with open(song.file, 'rb') as f:
                f.seek(range_start)

                # Just read as long as we have data to read.
                while left:
                    data = f.read(left if left < 8192 else 8192)
                    left -= len(data)
                    if not data:
                        break
                    self.write(data)
                    self.flush()
        else:
            # Transcode from starting point
            at = audiotranscode.AudioTranscode()
            stream = at.transcode_stream(song.file, settings.TRANSCODE_FORMAT)

            # First, seek to range_start
            seek_now = 0
            for data in stream:
                r_len = len(data)
                seek_now += r_len
                if seek_now == range_start:
                    break
                if seek_now > range_start:
                    w = seek_now-range_start
                    self.write(data[0:w])
                    self.flush()
                    left -= w
                    break

            # Just stream normally
            for data in stream:
                if left > 0:
                    rsize = len(data)

                    if left < rsize:
                        self.write(data[0:left])
                        left -= left
                    else:
                        self.write(data)
                        left -= rsize
                    self.flush()
                else:
                    break

        # Flush the last bytes before finishing up.
        self.flush()
        try:
            self.finish()
        except HTTPOutputError, o:
            log.error(o)


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
    app.listen(settings.PORT,  no_keep_alive=True)
    ioloop.IOLoop.instance().start()
    log.info("Stopping AudioStash server.")
