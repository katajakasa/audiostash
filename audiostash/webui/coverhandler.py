# -*- coding: utf-8 -*-

from audiostash import settings
import os
import mimetypes
import logging

from audiostash.common.tables import session_get, Cover, Session
from tornado import web, gen
from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger(__name__)


class CoverHandler(web.RequestHandler):
    @web.asynchronous
    @gen.coroutine
    def get(self, session_id, size_flag, cover_id):
        s = session_get()

        # Make sure session is valid
        try:
            s.query(Session).filter_by(key=session_id).one()
        except NoResultFound:
            s.close()
            self.set_status(401)
            self.finish("401")
            log.warning(u"Cover ID %d requested without a valid session.", cover_id)
            return

        # Find the cover we want
        try:
            cover = s.query(Cover).filter_by(id=cover_id).one()
        except NoResultFound:
            s.close()
            self.set_status(404)
            self.finish("404")
            log.warning(u"Cover ID %s does not exist.", cover_id)
            return

        s.close()

        if size_flag == "0":
            cover_file = os.path.join(settings.COVER_CACHE_DIRECTORY, "{}_small.jpg".format(cover.id))
        elif size_flag == "1":
            cover_file = os.path.join(settings.COVER_CACHE_DIRECTORY, "{}_medium.jpg".format(cover.id))
        else:
            # Make sure we have a filename
            if not cover.file:
                self.set_status(404)
                self.finish("404")
                log.warning(u"Cover file for ID %d is not set.", cover_id)
                return

            cover_file = cover.file

        # Just pick content type and dump out the file.
        self.set_header("Content-Type", mimetypes.guess_type("file://"+cover_file)[0])
        try:
            with file(cover_file, 'rb') as f:
                ret = yield gen.Task(self.get_data, f)
                self.write(ret)
        except IOError:
            self.set_status(404)
            self.finish("404")
            log.warning(u"Matching file for cover ID %d does not exist.", cover_id)
            return

        self.finish()

    def get_data(self, handle, callback):
        return callback(handle.read())
