# -*- coding: utf-8 -*-

import json
import logging

from passlib.hash import pbkdf2_sha256
from audiostash.common.tables import \
    session_get, Artist, Album, Playlist, PlaylistItem, Track, Setting, Session, User
from audiostash.common.utils import generate_session, to_isodate, from_isodate, utc_now, utc_minus_delta
from sockjs.tornado import SockJSConnection
from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger(__name__)


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
        log.debug(u"Sending error %s", msg)
        return self.send(msg)

    def send_message(self, mtype, message):
        msg = json.dumps({
            'type': mtype,
            'error': 0,
            'data': message,
        })
        log.debug(u"Sending message %s", msg)
        return self.send(msg)

    def on_open(self, info):
        self.authenticated = False
        self.ip = info.ip
        self.clients.add(self)
        log.debug(u"Connection accepted from %s", info.ip)

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
        s.close()

        # Session found with token.
        if session and user:
            self.sid = sid
            self.authenticated = True

            log.info(u"Authenticated with '%s'.", self.sid)

            # Send login success message
            self.send_message('auth', {
                'uid': user.id,
                'sid': sid,
                'level': user.level
            })
            return
        self.send_error('auth', "Invalid session", 403)
        log.warning(u"Authentication failed.")

    def on_login_msg(self, packet_msg):
        username = packet_msg.get('username', '')
        password = packet_msg.get('password', '')

        s = session_get()
        try:
            user = s.query(User).filter_by(username=username).one()
        except NoResultFound:
            self.send_error('login', 'Incorrect username or password', 401)
            log.warning(u"Invalid username or password in login request.")
            s.close()
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
            log.info(u"Logged in '%s'.", self.sid)

            # TODO: Cleanup old sessions

            # Send login success message
            self.send_message('login', {
                'uid': user.id,
                'sid': session_id,
                'level': user.level
            })
        else:
            self.send_error('login', 'Incorrect username or password', 401)
            log.warning(u"Invalid username or password in login request.")

        s.close()

    def on_logout_msg(self, packet_msg):
        # Remove session
        s = session_get()
        s.query(Session).filter_by(key=self.sid).delete()
        s.commit()
        s.close()

        # Dump out log
        log.info(u"Logged out '%s'.", self.sid)

        # Deauthenticate & clear session ID
        self.authenticated = False
        self.sid = None

    def on_playlist_msg(self, packet_msg):
        if not self.authenticated:
            return

        query = packet_msg.get('query', '')

        # Creates a new playlist with a given name. Errors out if the name already exists.
        if query == 'add_playlist':
            name = packet_msg.get('name')

            s = session_get()

            if s.query(Playlist).filter_by(name=name, deleted=False).count() > 0:
                self.send_error('playlist', "Playlist with given name already exists", 500)
                log.warning(u"Playlist with given name already exists.")
            else:
                playlist = Playlist(name=name, updated=utc_now())
                s.add(playlist)
                s.commit()
                self.sync_table('playlist', Playlist, utc_minus_delta(5), push=True)
                log.debug(u"A new playlist created!")

            s.close()
            return

        # Delete playlist and all related items
        if query == 'del_playlist':
            playlist_id = packet_msg.get('id')
            if id > 1:
                s = session_get()
                s.query(PlaylistItem).filter_by(playlist=playlist_id, deleted=False).update({
                    'deleted': True,
                    'updated': utc_now()
                })
                s.query(Playlist).filter_by(id=playlist_id).update({
                    'deleted': True,
                    'updated': utc_now()
                })
                s.commit()
                s.close()
                self.sync_table('playlist', Playlist, utc_minus_delta(5), push=True)
                self.sync_table('playlistitem', PlaylistItem, utc_minus_delta(5), push=True)
                self.notify_playlist_changes(playlist_id)
                log.debug(u"Playlist and items deleted!")
                return

        # Copy scratchpad playlist (id 1) to a new playlist
        if query == 'copy_scratchpad':
            to_id = packet_msg.get('id')
            s = session_get()
            s.query(PlaylistItem).filter_by(playlist=to_id, deleted=False).update({
                'deleted': True,
                'updated': utc_now()
            })
            s.commit()

            for item in s.query(PlaylistItem).filter_by(playlist=1, deleted=False):
                plitem = PlaylistItem(track=item.track, playlist=to_id, number=item.number, updated=utc_now())
                s.add(plitem)
            s.commit()
            s.close()

            self.sync_table('playlistitem', PlaylistItem, utc_minus_delta(5), push=True)
            self.notify_playlist_changes(to_id)
            log.debug(u"Playlist copied!")
            return

        # Saves tracks to the given playlist. Clears existing tracks.
        if query == 'save_playlist':
            playlist_id = packet_msg.get('id')
            items = packet_msg.get('tracks')

            s = session_get()
            s.query(PlaylistItem).filter_by(playlist=playlist_id, deleted=False).update({
                'deleted': True,
                'updated': utc_now()
            })

            k = 0
            for item in items:
                plitem = PlaylistItem(track=item['id'], playlist=playlist_id, number=k, updated=utc_now())
                s.add(plitem)
                k += 1
            s.commit()
            s.close()

            self.sync_table('playlistitem', PlaylistItem, utc_minus_delta(5), push=True)
            self.notify_playlist_changes(playlist_id)
            log.debug(u"Playlist updated!")
            return

    def notify_playlist_changes(self, playlist_id):
        self.send_message('playlist', {
            'query': 'update',
            'id': playlist_id,
            'push': True,
        })

    def sync_table(self, name, table, remote_ts, push=False):
        # Send message containing all new data in the table
        s = session_get()
        self.send_message('sync', {
            'query': 'request',
            'table': name,
            'ts': to_isodate(utc_now()),
            'push': push,
            'data': [t.serialize() for t in s.query(table).filter(table.updated > remote_ts)]
        })
        s.close()

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
                log.warning(u"Invalid timestamp in sync request.")
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
                self.sync_table(name, table, remote_ts)
            except KeyError:
                self.send_error('sync', "Invalid table name", 400)
                log.warning(u"Invalid table name in sync request.")
                return

    def on_unknown_msg(self, packet_msg):
        log.debug(u"Unknown or nonexistent packet type!")

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
            log.debug(u"Message: %s.", raw_message)
        else:
            log.debug(u"Message: **login**", ip=self.ip)

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
        log.debug(u"Connection closed")
        return super(AudioStashSock, self).on_close()
