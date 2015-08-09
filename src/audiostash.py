# -*- coding: utf-8 -*-

import json
import settings
import os
import mimetypes

from common.stashlog import StashLog

from passlib.hash import pbkdf2_sha256
from common.tables import \
    session_get, database_init, Artist, Album, Cover, Playlist, PlaylistItem, \
    Track, Setting, Session, User
from common.utils import generate_session, to_isodate, from_isodate, utc_now, utc_minus_delta
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
        log.warning("Authentication failed.", ip=self.ip)

    def on_login_msg(self, packet_msg):
        username = packet_msg.get('username', '')
        password = packet_msg.get('password', '')

        s = session_get()
        try:
            user = s.query(User).filter_by(username=username).one()
        except NoResultFound:
            self.send_error('login', 'Incorrect username or password', 401)
            log.warning("Invalid username or password in login request.", ip=self.ip)
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
            log.warning("Invalid username or password in login request.", ip=self.ip)
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

    def on_playlist_msg(self, packet_msg):
        if not self.authenticated:
            return

        query = packet_msg.get('query', '')
        if query == 'add_playlist':
            name = packet_msg.get('name')

            s = session_get()
            if s.query(Playlist).filter_by(name=name, deleted=False).count() > 0:
                self.send_error('playlist', "Playlist with given name already exists", 500)
                log.warning("Playlist with given name already exists.", ip=self.ip)
            else:
                playlist = Playlist(name=name, updated=utc_now())
                s.add(playlist)
                s.commit()
                self.sync_table('playlist', Playlist, utc_minus_delta(5))
                log.debug("A new playlist created!")
                return

        if query == 'del_playlist':
            playlist_id = packet_msg.get('id')
            if id > 1:
                s = session_get()
                s.query(PlaylistItem).filter_by(playlist=playlist_id, deleted=False).update({'deleted': True, 'updated': utc_now()})
                s.query(Playlist).filter_by(id=playlist_id).update({'deleted': True, 'updated': utc_now()})
                s.commit()
                self.sync_table('playlist', Playlist, utc_minus_delta(5))
                log.debug("Playlist deleted!")
                return

        if query == 'copy_scratchpad':
            to_id = packet_msg.get('id')
            s = session_get()
            s.query(PlaylistItem).filter_by(playlist=to_id, deleted=False).update({'deleted': True, 'updated': utc_now()})
            s.commit()

            for item in s.query(PlaylistItem).filter_by(playlist=1, deleted=False):
                plitem = PlaylistItem(track=item.track, playlist=to_id, number=item.number, updated=utc_now())
                s.add(plitem)
            s.commit()

            self.sync_table('playlistitem', PlaylistItem, utc_minus_delta(5))
            log.debug("Playlist copied!")
            return

        if query == 'save_playlist':
            playlist_id = packet_msg.get('id')
            items = packet_msg.get('tracks')

            s = session_get()
            s.query(PlaylistItem).filter_by(playlist=playlist_id, deleted=False).update({'deleted': True, 'updated': utc_now()})
            s.commit()
            k = 0
            for item in items:
                plitem = PlaylistItem(track=item['id'], playlist=playlist_id, number=k, updated=utc_now())
                s.add(plitem)
                k += 1
            s.commit()

            self.sync_table('playlistitem', PlaylistItem, utc_minus_delta(5))
            log.debug("Playlist updated!")
            return

    def sync_table(self, name, table, remote_ts):
        # Send message containing all new data in the table
        self.send_message('sync', {
            'query': 'request',
            'table': name,
            'ts': to_isodate(utc_now()),
            'data': [t.serialize() for t in session_get().query(table).filter(table.updated > remote_ts)]
        })

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
                log.warning("Invalid timestamp in sync request.", ip=self.ip)
                return

            # Find table model that matches the name
            try:
                table = {
                    'artist': Artist,
                    'album': Album,
                    'track': Track,
                    'setting': Setting,
                    'playlist': Playlist,
                    'playlistitem': PlaylistItem
                }[name]
            except KeyError:
                self.send_error('sync', "Invalid table name", 400)
                log.warning("Invalid table name in sync request.", ip=self.ip)
                return

            # Send message containing all new data in the table
            self.sync_table(name, table, remote_ts)

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
            'playlist': self.on_playlist_msg,
            'unknown': self.on_unknown_msg
        }
        cbs[packet_type if packet_type in cbs else 'unknown'](packet_msg)

    def on_close(self):
        self.clients.remove(self)
        log.debug("Connection closed", ip=self.ip)
        return super(AudioStashSock, self).on_close()


class CoverHandler(web.RequestHandler):
    @web.asynchronous
    @gen.coroutine
    def get(self, session_id, size_flag, cover_id):
        # Make sure session is valid
        try:
            session_get().query(Session).filter_by(key=session_id).one()
        except NoResultFound:
            self.set_status(401)
            self.finish("401")
            log.warning("Cover ID {} requested without a valid session.".format(cover_id))
            return

        # Find the cover we want
        try:
            cover = session_get().query(Cover).filter_by(id=cover_id).one()
        except NoResultFound:
            self.set_status(404)
            self.finish("404")
            log.warning("Cover ID {} does not exist.".format(cover_id))
            return

        if size_flag == "0":
            cover_file = os.path.join(settings.COVER_CACHE_DIRECTORY, "{}_small.jpg".format(cover.id))
        elif size_flag == "1":
            cover_file = os.path.join(settings.COVER_CACHE_DIRECTORY, "{}_medium.jpg".format(cover.id))
        else:
            # Find the cover we want
            try:
                cover = session_get().query(Cover).filter_by(id=cover_id).one()
            except NoResultFound:
                self.set_status(404)
                self.finish("404")
                log.warning("Cover ID {} does not exist.".format(cover_id))
                return

            # Make sure we have a filename
            if not cover.file:
                self.set_status(404)
                self.finish("404")
                log.warning("Cover file for ID {} is not set.".format(cover_id))
                return

            cover_file = cover.file

        # Just pick content type and dump out the file.
        self.set_header("Content-Type", mimetypes.guess_type("file://"+cover_file)[0])
        try:
            with file(cover_file, 'rb') as f:
                def get_data(callback):
                    callback(f.read())

                data = yield gen.Task(get_data)
                self.write(data)
        except IOError:
            self.set_status(404)
            self.finish("404")
            log.warning("Matching file for cover ID {} does not exist.".format(cover_id))
            return

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
            log.warning("Track ID {} requested without a valid session.".format(song_id))
            return

        # Find the song we want
        try:
            song = session_get().query(Track).filter_by(id=song_id).one()
        except NoResultFound:
            self.set_status(404)
            self.finish("404")
            log.warning("Nonexistent track ID {} requested.".format(song_id))
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
        if song.type in settings.NO_TRANSCODE_FORMATS:
            size = song.bytes_len
            song_file = song.file
            self.set_header("Content-Type", mimetypes.guess_type("file://"+song.file)[0])
        else:
            song_file = os.path.join(
                settings.MUSIC_CACHE_DIRECTORY,
                "{}.{}".format(song.id, settings.TRANSCODE_FORMAT))
            size = song.bytes_tc_len
            self.set_header("Content-Type", "audio/mpeg")

        # Set end range
        if not range_end or range_end >= size:
            range_end = size-1

        # Make sure range_start and range_end are withing size limits
        if range_start >= size:
            self.set_status(416)
            self.finish()
            return

        # Stream out
        try:
            with open(song_file, 'rb') as f:
                # Set range headers
                left = (range_end+1) - range_start
                self.set_header("Content-Length", left)
                self.set_header("Content-Range", "bytes {}-{}/{}".format(range_start, range_end, size))
                self.flush()

                # Forward to starting position
                f.seek(range_start)

                while left:
                    r = 1048576 if 1048576 < left else left

                    def get_data(callback):
                        callback(f.read(r))

                    data = yield gen.Task(get_data)
                    left -= r
                    self.write(data)
                    self.flush()
        except IOError:
            self.set_status(404)
            self.finish("404")
            log.error("Requested track ID {} doesn't exist.".format(song.id))
            return

        # Flush the last bytes before finishing up.
        self.flush()
        try:
            self.finish()
        except HTTPOutputError, o:
            log.error("Error while serving track ID {}: {}.".format(song_id, o))


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
    app.listen(settings.PORT)
    ioloop.IOLoop.instance().start()
    log.info("Stopping AudioStash server.")
