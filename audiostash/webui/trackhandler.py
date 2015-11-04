# -*- coding: utf-8 -*-

from audiostash import settings
import os
import mimetypes
import logging

from audiostash.common.tables import session_get, Track, Session
from tornado import web, gen
from tornado.httputil import HTTPOutputError
from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger(__name__)


class TrackHandler(web.RequestHandler):
    @web.asynchronous
    @gen.coroutine
    def get(self, session_id, song_id):
        s = session_get()

        # Make sure session is valid
        try:
            s.query(Session).filter_by(key=session_id).one()
        except NoResultFound:
            s.close()
            self.set_status(401)
            self.finish("401")
            log.warning(u"Track ID %d requested without a valid session.", song_id)
            return

        # Find the song we want
        try:
            song = s.query(Track).filter_by(id=song_id).one()
        except NoResultFound:
            s.close()
            self.set_status(404)
            self.finish("404")
            log.warning(u"Nonexistent track ID %d requested.", song_id)
            return

        s.close()

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

                # Forward to starting position and start reading data
                f.seek(range_start)
                while left:
                    r = 16384 if 16384 < left else left
                    data = yield gen.Task(self.get_data, (f, r))
                    self.write(data)
                    left -= r
        except IOError:
            self.set_status(404)
            self.finish("404")
            log.error(u"Requested track ID %d doesn't exist.", song.id)
            return

        # Flush the last bytes before finishing up.
        self.flush()
        try:
            self.finish()
        except HTTPOutputError, o:
            log.error(u"Error while serving track ID %d: %s.", song_id, str(o))

    def get_data(self, d, callback):
        return callback(d[0].read(d[1]))
